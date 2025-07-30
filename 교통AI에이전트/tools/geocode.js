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
const geocodeHandler = async ({ placeName }) => {
    const encodedPlaceName = encodeURIComponent(placeName);
    const response = await fetch(`https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodedPlaceName}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            Authorization: `KakaoAK ${process.env.KAKAO_REST_API_KEY}`,
        },
    });
    const data = await response.json();
    return {
        content: [{
                type: "text",
                text: JSON.stringify(data),
            }],
        isError: false,
    };
};
exports.geocodeHandler = geocodeHandler;
