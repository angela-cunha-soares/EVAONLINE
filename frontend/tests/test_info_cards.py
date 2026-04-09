"""Tests for frontend/components/info_cards.py."""

import dash_bootstrap_components as dbc
from dash import html
from frontend.components.info_cards import (
    create_fao_method_card,
    create_data_sources_card,
    create_evaonline_method_card,
    create_comparison_explanation_card,
    create_metrics_card,
    create_info_sidebar,
    create_collapsible_info_section,
)


class TestCreateFaoMethodCard:
    def test_returns_card(self):
        assert isinstance(create_fao_method_card(), dbc.Card)


class TestCreateDataSourcesCard:
    def test_returns_card(self):
        assert isinstance(create_data_sources_card(), dbc.Card)


class TestCreateEvaonlineMethodCard:
    def test_returns_card(self):
        assert isinstance(create_evaonline_method_card(), dbc.Card)


class TestCreateComparisonExplanationCard:
    def test_returns_card(self):
        assert isinstance(create_comparison_explanation_card(), dbc.Card)


class TestCreateMetricsCard:
    def test_default_no_args(self):
        assert isinstance(create_metrics_card(), dbc.Card)

    def test_with_metrics(self):
        metrics = {"r2": 0.95, "rmse": 0.5, "mbe": 0.1, "mae": 0.3, "kge": 0.9, "pbias": 2.5, "n_points": 365}
        interp = {"r2": "Excellent", "mae": "Low", "pbias": "Minimal", "kge": "High", "overall": "Very Good"}
        card = create_metrics_card(metrics=metrics, interpretation=interp)
        assert isinstance(card, dbc.Card)

    def test_with_interpretation(self):
        interp = {"overall": "Good", "notes": "Acceptable"}
        card = create_metrics_card(interpretation=interp)
        assert isinstance(card, dbc.Card)


class TestCreateInfoSidebar:
    def test_returns_div(self):
        result = create_info_sidebar()
        assert isinstance(result, html.Div)

    def test_with_metrics(self):
        m = {"r2": 0.9, "rmse": 0.5, "mbe": 0.1, "mae": 0.3, "kge": 0.85, "pbias": 3.0, "n_points": 100}
        i = {"r2": "Good", "mae": "Low", "pbias": "OK", "kge": "Good", "overall": "Good"}
        result = create_info_sidebar(metrics=m, interpretation=i)
        assert result is not None


class TestCreateCollapsibleInfoSection:
    def test_returns_accordion(self):
        result = create_collapsible_info_section()
        assert isinstance(result, dbc.Accordion)

    def test_with_metrics(self):
        m = {"r2": 0.9, "rmse": 0.5, "mbe": 0.1, "mae": 0.3, "kge": 0.85, "pbias": 3.0, "n_points": 100}
        i = {"r2": "Good", "mae": "Low", "pbias": "OK", "kge": "Good", "overall": "Good"}
        result = create_collapsible_info_section(metrics=m, interpretation=i)
        assert result is not None
