"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const mcp_js_1 = require("@modelcontextprotocol/sdk/server/mcp.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
const directionSearchByCoordinates_js_1 = require("./tools/directionSearchByCoordinates.js");
const directionSearchByAddress_js_1 = require("./tools/directionSearchByAddress.js");
const addressSearchByPlaceName_js_1 = require("./tools/addressSearchByPlaceName.js");
const geocode_js_1 = require("./tools/geocode.js");
const futureDirectionSearchByCoordinates_js_1 = require("./tools/futureDirectionSearchByCoordinates.js");
const multiDestinationDirectionSearch_js_1 = require("./tools/multiDestinationDirectionSearch.js");
// Create an MCP server
const server = new mcp_js_1.McpServer({
    name: "Traffic Data MCP Server",
    version: "1.0.2",
});
// Register tools
server.tool("direction_search_by_coords", "Search for directions between two points using their coordinates (longitude and latitude). This tool provides navigation information including distance, duration, and route details.", directionSearchByCoordinates_js_1.directionSearchByCoordinatesSchema, directionSearchByCoordinates_js_1.directionSearchByCoordinatesHandler);
server.tool("direction_search_by_address", "Search for directions between two locations using their addresses. The tool first geocodes the addresses to coordinates, then finds the optimal route between them.", directionSearchByAddress_js_1.directionSearchByAddressSchema, directionSearchByAddress_js_1.directionSearchByAddressHandler);
server.tool("address_search_by_place_name", "Search for addresses using a place name or keyword. Returns detailed location information including coordinates and address details.", addressSearchByPlaceName_js_1.addressSearchByPlaceNameSchema, addressSearchByPlaceName_js_1.addressSearchByPlaceNameHandler);
server.tool("geocode", "Convert an address into geographic coordinates (geocoding). Returns the exact location coordinates and address details for the given place name.", geocode_js_1.geocodeSchema, geocode_js_1.geocodeHandler);
server.tool("future_direction_search_by_coords", "Search for directions with future departure time. Provides navigation information considering traffic predictions for a specific future time. Supports various options like waypoints, route preferences, and vehicle details.", futureDirectionSearchByCoordinates_js_1.futureDirectionSearchByCoordinatesSchema, futureDirectionSearchByCoordinates_js_1.futureDirectionSearchByCoordinatesHandler);
server.tool("multi_destination_direction_search", "Search for directions between a starting point and multiple destinations with coordinates. Returns a summary of the route including distance, duration, and route details. For detailed route information, additional calls to the car navigation API are required.", multiDestinationDirectionSearch_js_1.multiDestinationDirectionSearchSchema, multiDestinationDirectionSearch_js_1.multiDestinationDirectionSearchHandler);
(async () => {
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
})();
