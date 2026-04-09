/**
 * Client-side chart download helper.
 *
 * Called by Dash clientside_callback to export a Plotly chart
 * as PNG or JPG in high resolution.
 */

// Namespace for Dash clientside callbacks
if (!window.dash_clientside) {
    window.dash_clientside = {};
}
if (!window.dash_clientside.chart_download) {
    window.dash_clientside.chart_download = {};
}

/**
 * Download a Plotly graph as an image.
 *
 * @param {number} nClicks - button click count (trigger)
 * @param {string} graphId - the id of the dcc.Graph element
 * @param {string} format  - "png" or "jpeg"
 * @param {string} filename - base filename (without extension)
 * @returns {string} empty string (Dash requires an Output)
 */
window.dash_clientside.chart_download.download = function (nClicks, graphId, format, filename) {
    if (!nClicks) {
        return window.dash_clientside.no_update;
    }

    var graphDiv = document.getElementById(graphId);
    if (!graphDiv) {
        console.warn("Chart not found: " + graphId);
        return window.dash_clientside.no_update;
    }

    var ext = (format === "jpeg") ? "jpg" : "png";

    Plotly.downloadImage(graphDiv, {
        format: format,
        width: 1920,
        height: 1080,
        scale: 2,
        filename: filename + "." + ext
    });

    return "";
};
