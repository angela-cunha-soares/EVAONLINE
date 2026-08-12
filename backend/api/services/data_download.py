from datetime import datetime, timedelta
from typing import List, Tuple, Union

import numpy as np
import pandas as pd
from loguru import logger

# Imports from canonical validation modules
try:
    from backend.api.services.climate_validation import (
        ClimateValidationService,
    )
    from backend.api.services.climate_source_manager import (
        ClimateSourceManager,
    )

except ImportError:
    from ...api.services.climate_validation import (
        ClimateValidationService,
    )
    from ...api.services.climate_source_manager import (
        ClimateSourceManager,
    )


async def download_weather_data(
    data_source: Union[str, list],
    data_inicial: str,
    data_final: str,
    longitude: float,
    latitude: float,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Download weather data from specified sources for coordinates and period.

    Complete integration with validation and selection modules:
    - climate_validation.py: Validates coordinates, dates and mode
    - climate_source_manager.py: Selects sources by location and mode

    Supported sources:
    - "nasa_power": NASA POWER (global, 1990+, public domain)
    - "openmeteo_archive": Open-Meteo Archive (global, 1990+, CC BY 4.0)
    - "openmeteo_forecast": Open-Meteo Forecast (global, today±5d, CC BY 4.0)
    - "met_norway": MET Norway Locationforecast (global, CC BY 4.0)
    - "nws_forecast": NWS Forecast (USA, forecasts, public domain)
    - "nws_stations": NWS Stations (USA, stations, public domain)
    - "data fusion": Fuses multiple available sources (Kalman Ensemble)

    Args:
        data_source: Data source (str or list of sources)
        data_inicial: Start date in YYYY-MM-DD format
        data_final: End date in YYYY-MM-DD format
        longitude: Longitude (-180 to 180)
        latitude: Latitude (-90 to 90)
    """
    logger.info(
        f"Starting download - Source: {data_source}, "
        f"Period: {data_inicial} to {data_final}, "
        f"Coord: ({latitude}, {longitude})"
    )
    warnings_list = []

    # 1. COORDINATE VALIDATION
    coord_valid, coord_details = ClimateValidationService.validate_coordinates(
        lat=latitude, lon=longitude, location_name="Download Request"
    )
    if not coord_valid:
        msg = f"Invalid coordinates: {coord_details.get('errors')}"
        logger.error(msg)
        raise ValueError(msg)

    # 2. DATE FORMAT VALIDATION
    date_valid, date_details = ClimateValidationService.validate_date_range(
        start_date=data_inicial,
        end_date=data_final,
        allow_future=True,  # Allow forecast
        max_future_days=6,  # Forecast: today + 6 days (timezone tolerance)
    )
    if not date_valid:
        msg = f"Invalid dates: {date_details.get('errors')}"
        logger.error(msg)
        raise ValueError(msg)

    # Convert to pandas datetime for calculations
    data_inicial_formatted = pd.to_datetime(data_inicial)
    data_final_formatted = pd.to_datetime(data_final)
    period_days = date_details["period_days"]

    # Define today for use throughout function
    today = datetime.now().date()

    # 3. MODE DETECTION (using official module)
    detected_mode, error = ClimateValidationService.detect_mode_from_dates(
        data_inicial, data_final
    )
    if not detected_mode:
        warnings_list.append(f"Mode not detected: {error}")
        # Use default mode based on dates
        end_date_obj = pd.to_datetime(data_final).date()
        if end_date_obj > today:
            detected_mode = "dashboard_forecast"
        else:
            detected_mode = "dashboard_current"
        logger.warning(
            f"Using default mode: {detected_mode} (dates don't fit "
            f"perfectly into modes)"
        )

    # 4. MODE AND PERIOD VALIDATION
    mode_valid, mode_details = ClimateValidationService.validate_request_mode(
        mode=detected_mode,
        start_date=data_inicial,
        end_date=data_final,
        lat=latitude,
        lng=longitude,
    )
    if not mode_valid:
        # Add warnings but don't fail (may be manual request)
        mode_errors = mode_details.get("errors", [])
        warnings_list.extend(
            [f"Mode {detected_mode} warning: {err}" for err in mode_errors]
        )
        logger.warning(
            f"Mode {detected_mode} validation with warnings: {mode_errors}"
        )

    logger.info(f"Detected mode: {detected_mode}")

    # 5. INTELLIGENT SOURCE SELECTION (using ClimateSourceManager)
    source_manager = ClimateSourceManager()

    # 6. Normalize data_source input
    if isinstance(data_source, list):
        requested_sources = [str(s).lower() for s in data_source]
    else:
        data_source_str = str(data_source).lower()
        if "," in data_source_str:
            requested_sources = [s.strip() for s in data_source_str.split(",")]
        else:
            requested_sources = [data_source_str]

    # 7. Use specific method for data_download
    if "data fusion" in requested_sources:
        # Data Fusion: use automatic selection based on mode and location
        try:
            source_result = source_manager.get_sources_for_data_download(
                lat=latitude,
                lon=longitude,
                start_date=pd.to_datetime(data_inicial).date(),
                end_date=pd.to_datetime(data_final).date(),
                mode=detected_mode,
                preferred_sources=None,  # Use all available
            )
            sources = source_result["sources"]
            warnings_list.extend(source_result["warnings"])

            logger.info(
                f"Data Fusion {detected_mode}: {len(sources)} sources "
                f"selected - {sources}"
            )
        except ValueError as e:
            msg = f"Error selecting sources for Data Fusion: {str(e)}"
            logger.error(msg)
            raise ValueError(msg)
    else:
        # Specific source(s): validate availability
        try:
            source_result = source_manager.get_sources_for_data_download(
                lat=latitude,
                lon=longitude,
                start_date=pd.to_datetime(data_inicial).date(),
                end_date=pd.to_datetime(data_final).date(),
                mode=detected_mode,
                preferred_sources=requested_sources,
            )
            sources = source_result["sources"]
            warnings_list.extend(source_result["warnings"])

            # Some requested sources may not cover the TAIL of the range
            # (NASA POWER / Open-Meteo Archive have a ~2-3 day lag, while the
            # Recent mode ends today). That is expected in the multi-source
            # design: Open-Meteo Forecast fills the recent gap. So we proceed
            # with whatever is available and only fail if NOTHING is available
            # (handled just below by the "No sources available" check).
            unavailable = set(requested_sources) - set(sources)
            if unavailable:
                warn = (
                    f"Sources partially unavailable for "
                    f"({latitude}, {longitude}): {unavailable}. "
                    f"Proceeding with: {sources}"
                )
                warnings_list.append(warn)
                logger.warning(warn)

            logger.info(f"Sources selected: {sources}")
        except ValueError as e:
            msg = f"Error validating sources: {str(e)}"
            logger.error(msg)
            raise ValueError(msg)

    if not sources:
        msg = "No sources available for this request"
        logger.error(msg)
        raise ValueError(msg)

    weather_data_sources: List[pd.DataFrame] = []
    for source in sources:
        logger.info(f"Processing source: {source}")

        # Temporal limit validations
        # Each client (adapter) validates its own internal limits
        # NO need to validate here (duplication removed)
        # Canonical limits in: climate_source_availability.py
        data_final_adjusted = data_final_formatted

        # Download data
        # NOTE: Temporal limit validations are done by
        # clients/adapters themselves. Each API knows its limits
        # and validates internally.
        # Initialize variables
        weather_df = None

        try:
            if source == "nasa_power":
                from backend.api.services.nasa_power import (
                    nasa_power_sync_adapter,
                )

                NASAPowerSyncAdapter = (
                    nasa_power_sync_adapter.NASAPowerSyncAdapter
                )

                client = NASAPowerSyncAdapter()
                nasa_data = client.get_daily_data_sync(
                    lat=latitude,
                    lon=longitude,
                    start_date=data_inicial_formatted,
                    end_date=data_final_adjusted,
                )

                # Convert to pandas DataFrame - NASA POWER variables
                data_records = []
                for record in nasa_data:
                    data_records.append(
                        {
                            "date": record.date,
                            "T2M_MAX": record.temp_max,
                            "T2M_MIN": record.temp_min,
                            "T2M": record.temp_mean,
                            "RH2M": record.humidity,
                            "WS2M": record.wind_speed,
                            "ALLSKY_SFC_SW_DWN": record.solar_radiation,
                            "PRECTOTCORR": record.precipitation,
                        }
                    )

                weather_df = pd.DataFrame(data_records)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df.set_index("date", inplace=True)
                weather_df["source"] = "nasa_power"

                logger.info(
                    f"NASA POWER: {len(nasa_data)} daily records "
                    f"for ({latitude}, {longitude})"
                )

            elif source == "openmeteo_archive":
                # Open-Meteo Archive (historical since 1950)
                # IMPORTANT: end_date must be <= ~today - 3 days (variable delay)
                from backend.api.services.openmeteo_archive import (
                    openmeteo_archive_sync_adapter,
                )

                OpenMeteoArchiveSyncAdapter = (
                    openmeteo_archive_sync_adapter.OpenMeteoArchiveSyncAdapter
                )

                # Adjust end_date for Archive API limit
                archive_max_date = (today - timedelta(days=3)).strftime(
                    "%Y-%m-%d"
                )
                archive_max_date_dt = pd.to_datetime(archive_max_date)
                data_final_dt = pd.to_datetime(data_final_adjusted)
                archive_end_date = min(data_final_dt, archive_max_date_dt)
                archive_end_date_str = archive_end_date.strftime("%Y-%m-%d")

                # Skip if start_date > archive_max_date
                data_inicial_dt = pd.to_datetime(data_inicial_formatted)
                if data_inicial_dt > archive_max_date_dt:
                    logger.info(
                        f"Open-Meteo Archive skipped: requested period "
                        f"({data_inicial_formatted} to {data_final_adjusted}) "
                        f"is after archive limit ({archive_max_date})"
                    )
                    continue

                client = OpenMeteoArchiveSyncAdapter()
                openmeteo_data = client.get_daily_data_sync(
                    lat=latitude,
                    lon=longitude,
                    start_date=data_inicial_formatted,
                    end_date=archive_end_date_str,
                )

                if not openmeteo_data:
                    msg = (
                        f"No data from Open-Meteo Archive for "
                        f"({latitude}, {longitude}) "
                        f"between {data_inicial} and {data_final}"
                    )
                    logger.warning(msg)
                    warnings_list.append(msg)
                    continue

                # Convert to DataFrame - ALL Open-Meteo variables
                weather_df = pd.DataFrame(openmeteo_data)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df.set_index("date", inplace=True)

                # Harmonize OpenMeteo -> NASA format for ETo
                # ETo: T2M_MAX, T2M_MIN, T2M (mean), RH2M, WS2M,
                # ALLSKY_SFC_SW_DWN, PRECTOTCORR
                harmonization = {
                    "temperature_2m_max": "T2M_MAX",
                    "temperature_2m_min": "T2M_MIN",
                    "temperature_2m_mean": "T2M",
                    "relative_humidity_2m_mean": "RH2M",
                    "wind_speed_2m_mean": "WS2M",
                    "shortwave_radiation_sum": "ALLSKY_SFC_SW_DWN",
                    "precipitation_sum": "PRECTOTCORR",
                }

                for openmeteo_var, nasa_var in harmonization.items():
                    if openmeteo_var in weather_df.columns:
                        weather_df[nasa_var] = weather_df[openmeteo_var]

                weather_df["source"] = "openmeteo_archive"

                logger.info(
                    f"Open-Meteo Archive: {len(openmeteo_data)} "
                    f"daily records for ({latitude}, {longitude})"
                )

            elif source == "openmeteo_forecast":
                # Open-Meteo Forecast (forecast + recent: -90d to +5d)
                from backend.api.services.openmeteo_forecast import (
                    openmeteo_forecast_sync_adapter,
                )

                OpenMeteoForecastSyncAdapter = (
                    openmeteo_forecast_sync_adapter.OpenMeteoForecastSyncAdapter
                )

                # Clamp dates to OM Forecast window: today-90d to today+5d
                forecast_min_date = pd.to_datetime(
                    (today - timedelta(days=90)).strftime("%Y-%m-%d")
                )
                forecast_max_date = pd.to_datetime(
                    (today + timedelta(days=5)).strftime("%Y-%m-%d")
                )
                fc_start = max(
                    pd.to_datetime(data_inicial_formatted), forecast_min_date
                )
                fc_end = min(
                    pd.to_datetime(data_final_formatted), forecast_max_date
                )

                # Skip if clamped range is invalid
                if fc_start > fc_end:
                    logger.info(
                        f"Open-Meteo Forecast skipped: requested period "
                        f"({data_inicial_formatted} to {data_final_formatted}) "
                        f"is outside forecast window "
                        f"({forecast_min_date.date()} to {forecast_max_date.date()})"
                    )
                    continue

                client = OpenMeteoForecastSyncAdapter()
                forecast_data = client.get_daily_data_sync(
                    lat=latitude,
                    lon=longitude,
                    start_date=fc_start,
                    end_date=fc_end,
                )

                if not forecast_data:
                    msg = (
                        f"No data from Open-Meteo Forecast for "
                        f"({latitude}, {longitude}) "
                        f"between {data_inicial} and {data_final}"
                    )
                    logger.warning(msg)
                    warnings_list.append(msg)
                    continue

                # Convert to DataFrame - ALL Open-Meteo variables
                weather_df = pd.DataFrame(forecast_data)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df.set_index("date", inplace=True)

                # Harmonize OpenMeteo -> NASA format for ETo
                # ETo: T2M_MAX, T2M_MIN, T2M (mean), RH2M, WS2M,
                # ALLSKY_SFC_SW_DWN, PRECTOTCORR
                harmonization = {
                    "temperature_2m_max": "T2M_MAX",
                    "temperature_2m_min": "T2M_MIN",
                    "temperature_2m_mean": "T2M",
                    "relative_humidity_2m_mean": "RH2M",
                    "wind_speed_2m_mean": "WS2M",
                    "shortwave_radiation_sum": "ALLSKY_SFC_SW_DWN",
                    "precipitation_sum": "PRECTOTCORR",
                }

                # Rename existing columns
                for openmeteo_var, nasa_var in harmonization.items():
                    if openmeteo_var in weather_df.columns:
                        weather_df[nasa_var] = weather_df[openmeteo_var]

                weather_df["source"] = "openmeteo_forecast"

                logger.info(
                    f"Open-Meteo Forecast: {len(forecast_data)} "
                    f"daily records for ({latitude}, {longitude})"
                )

            elif source == "met_norway":
                # MET Norway Locationforecast (Global, async)
                from backend.api.services.met_norway.met_norway_client import (
                    METNorwayClient,
                )

                client = METNorwayClient()
                met_data = await client.get_daily_forecast(
                    lat=latitude,
                    lon=longitude,
                    start_date=data_inicial_formatted,
                    end_date=data_final_adjusted,
                )

                if not met_data:
                    msg = (
                        f"No data from MET Norway for "
                        f"({latitude}, {longitude}) "
                        f"between {data_inicial} and {data_final}"
                    )
                    logger.warning(msg)
                    warnings_list.append(msg)
                    continue

                # Get recommended variables for region
                from backend.api.services.met_norway.met_norway_client import (
                    METNorwayClient,
                )

                recommended_vars = METNorwayClient.get_recommended_variables(
                    latitude, longitude
                )

                # Check if precipitation should be included
                include_precipitation = "precipitation_sum" in recommended_vars

                # Log regional strategy
                if include_precipitation:
                    region_info = (
                        "Nordic Region: using high-quality "
                        "precipitation (1km + radar)"
                    )
                else:
                    region_info = (
                        "Global: using temperature/humidity only "
                        "(precipitation from Open-Meteo)"
                    )

                logger.info(f"MET Norway - {region_info}")

                # Convert to DataFrame - FILTER variables by region
                data_records = []
                for record in met_data:
                    # Handle both dict and object formats
                    if isinstance(record, dict):
                        row = {
                            "date": record.get("date"),
                            "temp_max": record.get("temp_max"),
                            "temp_min": record.get("temp_min"),
                            "temp_mean": record.get("temp_mean"),
                            "humidity_mean": record.get("humidity_mean"),
                        }
                        if include_precipitation:
                            row["precipitation_sum"] = record.get(
                                "precipitation_sum"
                            )
                    else:
                        row = {
                            "date": record.date,
                            "temp_max": record.temp_max,
                            "temp_min": record.temp_min,
                            "temp_mean": record.temp_mean,
                            "humidity_mean": record.humidity_mean,
                        }
                        if include_precipitation:
                            row["precipitation_sum"] = record.precipitation_sum
                    data_records.append(row)

                weather_df = pd.DataFrame(data_records)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df.set_index("date", inplace=True)

                # Harmonize MET Norway -> NASA schema for fusion
                met_harmonization = {
                    "temp_max": "T2M_MAX",
                    "temp_min": "T2M_MIN",
                    "temp_mean": "T2M",
                    "humidity_mean": "RH2M",
                    "precipitation_sum": "PRECTOTCORR",
                }
                for met_var, nasa_var in met_harmonization.items():
                    if met_var in weather_df.columns:
                        weather_df[nasa_var] = weather_df[met_var]

                weather_df["source"] = "met_norway"

                # Add CC-BY 4.0 attribution to warnings
                warnings_list.append(
                    "MET Norway data: CC-BY 4.0 - Attribution required"
                )

                # Log included variables
                logger.info(
                    "MET Norway: %d records (%s, %s), " "variables: %s",
                    len(met_data),
                    latitude,
                    longitude,
                    list(weather_df.columns),
                )

            elif source == "nws_forecast":
                # NWS Forecast (USA, forecasts)
                from backend.api.services.nws_forecast import (
                    nws_forecast_sync_adapter,
                )

                NWSDailyForecastSyncAdapter = (
                    nws_forecast_sync_adapter.NWSDailyForecastSyncAdapter
                )

                client = NWSDailyForecastSyncAdapter()
                nws_forecast_data = client.get_daily_data_sync(
                    lat=latitude,
                    lon=longitude,
                    start_date=data_inicial_formatted,
                    end_date=data_final_adjusted,
                )

                if not nws_forecast_data:
                    msg = (
                        f"No data from NWS Forecast for "
                        f"({latitude}, {longitude}) "
                        f"between {data_inicial} and {data_final}"
                    )
                    logger.warning(msg)
                    warnings_list.append(msg)
                    continue

                # Convert to DataFrame - NWS Forecast variables
                data_records = []
                for record in nws_forecast_data:
                    data_records.append(
                        {
                            "date": record.date,
                            "temp_max": record.temp_max,
                            "temp_min": record.temp_min,
                            "temp_mean": record.temp_mean,
                            "humidity_mean": record.humidity_mean,
                            "wind_speed_2m_mean": record.wind_speed_mean,
                            "precipitation_sum": record.precipitation_sum,
                            "solar_radiation": record.solar_radiation,
                            "pressure_mean": record.pressure_mean,
                            "dewpoint_mean": record.dewpoint_mean,
                        }
                    )

                weather_df = pd.DataFrame(data_records)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df.set_index("date", inplace=True)

                # Harmonize NWS -> NASA schema for fusion
                nws_harmonization = {
                    "temp_max": "T2M_MAX",
                    "temp_min": "T2M_MIN",
                    "temp_mean": "T2M",
                    "humidity_mean": "RH2M",
                    "wind_speed_2m_mean": "WS2M",
                    "solar_radiation": "ALLSKY_SFC_SW_DWN",
                    "precipitation_sum": "PRECTOTCORR",
                }
                for nws_var, nasa_var in nws_harmonization.items():
                    if nws_var in weather_df.columns:
                        weather_df[nasa_var] = weather_df[nws_var]

                weather_df["source"] = "nws_forecast"

                logger.info(
                    "NWS Forecast: %d records (%s, %s)",
                    len(nws_forecast_data),
                    latitude,
                    longitude,
                )

            elif source == "nws_stations":
                from backend.api.services.nws_stations import (
                    nws_stations_sync_adapter,
                )

                NWSStationsSyncAdapter = (
                    nws_stations_sync_adapter.NWSStationsSyncAdapter
                )

                client = NWSStationsSyncAdapter()
                # NWS Stations implementation would go here

        except Exception as e:
            logger.error(
                f"{source}: error downloading data: {str(e)}",
                exc_info=True,
            )
            warnings_list.append(f"{source}: error downloading data: {str(e)}")
            continue

        # Validate DataFrame
        if weather_df is None or weather_df.empty:
            msg = (
                f"No data obtained from {source} for "
                f"({latitude}, {longitude}) "
                f"between {data_inicial} and {data_final}"
            )
            logger.warning(msg)
            warnings_list.append(msg)
            continue

        # Don't standardize columns - preserve native API names
        # Each API returns its own specific variables
        # Validation will be done in data_preprocessing.py with
        # appropriate limits
        weather_df = weather_df.replace(-999.00, np.nan)
        weather_df = weather_df.dropna(how="all", subset=weather_df.columns)

        # Check data quantity
        days_returned = (
            weather_df.index.max() - weather_df.index.min()
        ).days + 1
        if days_returned < period_days:
            msg = (
                f"{source}: obtained {days_returned} days "
                f"(requested: {period_days})"
            )
            warnings_list.append(msg)

        # Check missing data
        perc_missing = weather_df.isna().mean() * 100
        variable_names = {
            # NASA POWER
            "ALLSKY_SFC_SW_DWN": "Solar Radiation (MJ/m²/day)",
            "PRECTOTCORR": "Total Precipitation (mm)",
            "T2M_MAX": "Maximum Temperature (°C)",
            "T2M_MIN": "Minimum Temperature (°C)",
            "T2M": "Mean Temperature (°C)",
            "RH2M": "Relative Humidity (%)",
            "WS2M": "Wind Speed (m/s)",
            # Open-Meteo (Archive & Forecast)
            "temperature_2m_max": "Maximum Temperature (°C)",
            "temperature_2m_min": "Minimum Temperature (°C)",
            "temperature_2m_mean": "Mean Temperature (°C)",
            "relative_humidity_2m_max": "Maximum Relative Humidity (%)",
            "relative_humidity_2m_min": "Minimum Relative Humidity (%)",
            "relative_humidity_2m_mean": "Mean Relative Humidity (%)",
            "wind_speed_10m_mean": "Mean Wind Speed (m/s)",
            "wind_speed_10m_max": "Maximum Wind Speed (m/s)",
            "shortwave_radiation_sum": "Solar Radiation (MJ/m²/day)",
            "precipitation_sum": "Total Precipitation (mm)",
            "et0_fao_evapotranspiration": "ETo FAO-56 (mm/day)",
            # MET Norway
            # (same variables as Open-Meteo, as they are harmonized)
            # Variables already listed above in Open-Meteo section
            # NWS Stations - Station observations (no precipitation)
        }

        for var_name, percentage in perc_missing.items():
            if percentage > 25:
                var_display = variable_names.get(str(var_name), str(var_name))
                warnings_list.append(
                    f"{source}: {var_display} has "
                    f"{percentage:.1f}% missing data"
                )

        # Log dados de cada fonte para debug da fusão
        min_date = weather_df.index.min()
        max_date = weather_df.index.max()
        logger.info(
            f"📦 {source.upper()}: {len(weather_df)} dias obtidos "
            f"({min_date.date()} a {max_date.date()})"
        )

        # Mostrar primeiras linhas com variáveis principais
        display_cols = []
        key_vars = [
            "T2M_MAX",
            "T2M_MIN",
            "T2M",
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "temp_max",
            "temp_min",
            "temp_mean",
            "RH2M",
            "relative_humidity_2m_mean",
            "humidity_mean",
            "WS2M",
            "wind_speed_10m_mean",
            "wind_speed_2m_mean",
            "ALLSKY_SFC_SW_DWN",
            "shortwave_radiation_sum",
            "PRECTOTCORR",
            "precipitation_sum",
        ]
        for col in weather_df.columns:
            if col in key_vars:
                display_cols.append(col)

        if display_cols:
            logger.info(f"   Variáveis: {', '.join(display_cols)}")
            # Mostrar primeiros 3 registros
            sample_df = weather_df.head(3)[display_cols]
            logger.info(f"\n{sample_df.to_string()}")

        weather_data_sources.append(weather_df)
        logger.debug("%s: DataFrame completo\n%s", source, weather_df)

    # 8. Consolidate data (Kalman fusion will be done in eto_services.py)
    if not weather_data_sources:
        msg = "No sources provided valid data"
        logger.error(msg)
        raise ValueError(msg)

    # 9. If multiple sources, concatenate ALL measurements:
    # Kalman fusion in eto_services.py will apply intelligent weights
    if len(weather_data_sources) > 1:
        logger.info(
            f"Concatenating {len(weather_data_sources)} sources "
            f"(Kalman fusion will be applied in eto_services.py)"
        )
        weather_data = pd.concat(weather_data_sources, axis=0)
        # KEEP date duplicates - each row represents 1 source
        # Kalman fusion will process all measurements
        logger.info(
            f"Total of {len(weather_data)} measurements from "
            f"{len(weather_data_sources)} sources for fusion"
        )
    else:
        weather_data = weather_data_sources[0]

    # Final validation - accept all API variables
    # No longer restrict to only NASA POWER variables
    # 10. Physical validation will be done in data_preprocessing.py

    logger.info("Final data obtained successfully")
    logger.debug("Final DataFrame:\n%s", weather_data)
    return weather_data, warnings_list
