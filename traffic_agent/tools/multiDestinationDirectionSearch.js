"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.multiDestinationDirectionSearchHandler = exports.multiDestinationDirectionSearchSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
const kakaoFetch_js_1 = require("./kakaoFetch.js");
dotenv_1.default.config();
exports.multiDestinationDirectionSearchSchema = {
    origin: zod_1.z.object({
        name: zod_1.z.string().optional(),
        x: zod_1.z.number().describe("Origin X coordinate (longitude)"),
        y: zod_1.z.number().describe("Origin Y coordinate (latitude)"),
    }).describe("Origin"),
    destinations: zod_1.z.array(zod_1.z.object({
        key: zod_1.z.string().describe("Any string that identifies the destination"),
        x: zod_1.z.number().describe("Destination X coordinate (longitude)"),
        y: zod_1.z.number().describe("Destination Y coordinate (latitude)"),
    })).max(30).describe("Destinations (up to 30)"),
    radius: zod_1.z.number().int().max(10000).describe("Routing radius in meters (max 10000)"),
    priority: zod_1.z.enum(["TIME", "DISTANCE"]).optional().describe("Route priority (TIME: fastest, DISTANCE: shortest)"),
    avoid: zod_1.z.array(zod_1.z.enum(["ferries", "toll", "motorway", "schoolzone", "uturn"])).optional().describe("Road types to avoid"),
    roadevent: zod_1.z.number().int().min(0).max(2).optional().describe("Road-closure handling (0: apply all, 1: ignore near origin/destination, 2: ignore all)"),
};
const multiDestinationDirectionSearchHandler = async (params) => {
    const { origin, destinations, radius, priority, avoid, roadevent } = params;
    const requestBody = Object.assign(Object.assign(Object.assign({ origin,
        destinations,
        radius }, (priority && { priority })), (avoid && { avoid })), (roadevent !== undefined && { roadevent }));
    const result = await kakaoFetch_js_1.kakaoFetchJson("https://apis-navi.kakaomobility.com/v1/destinations/directions", {
        method: "POST",
        headers: kakaoFetch_js_1.kakaoHeaders(),
        body: JSON.stringify(requestBody),
    });
    if (!result.ok) {
        return kakaoFetch_js_1.toolError(`multi_destination_direction_search failed: ${result.error}`);
    }
    return kakaoFetch_js_1.toolSuccess(result.data);
};
exports.multiDestinationDirectionSearchHandler = multiDestinationDirectionSearchHandler;
