"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.directionSearchByCoordinatesHandler = exports.directionSearchByCoordinatesSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.directionSearchByCoordinatesSchema = {
    originLongitude: zod_1.z.number(),
    originLatitude: zod_1.z.number(),
    destLongitude: zod_1.z.number(),
    destLatitude: zod_1.z.number(),
};
const kakaoFetch_js_1 = require("./kakaoFetch.js");
const directionSearchByCoordinatesHandler = async ({ originLongitude, originLatitude, destLongitude, destLatitude, }) => {
    const result = await kakaoFetch_js_1.kakaoFetchJson(`https://apis-navi.kakaomobility.com/v1/directions?origin=${originLongitude},${originLatitude}&destination=${destLongitude},${destLatitude}`, {
        method: "GET",
        headers: kakaoFetch_js_1.kakaoHeaders(),
    });
    if (!result.ok) {
        return kakaoFetch_js_1.toolError(`direction_search_by_coords failed: ${result.error}`);
    }
    return kakaoFetch_js_1.toolSuccess(result.data);
};
exports.directionSearchByCoordinatesHandler = directionSearchByCoordinatesHandler;
