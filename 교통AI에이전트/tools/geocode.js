"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.geocodeHandler = exports.geocodeSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.geocodeSchema = {
    placeName: zod_1.z.string(),
};
const kakaoFetch_js_1 = require("./kakaoFetch.js");
const geocodeHandler = async ({ placeName }) => {
    const encodedPlaceName = encodeURIComponent(placeName);
    const result = await kakaoFetch_js_1.kakaoFetchJson(`https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodedPlaceName}`, {
        method: "GET",
        headers: kakaoFetch_js_1.kakaoHeaders(),
    });
    if (!result.ok) {
        return kakaoFetch_js_1.toolError(`geocode failed: ${result.error}`);
    }
    return kakaoFetch_js_1.toolSuccess(result.data);
};
exports.geocodeHandler = geocodeHandler;
