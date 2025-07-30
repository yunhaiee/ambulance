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
const directionSearchByCoordinatesHandler = async ({ originLongitude, originLatitude, destLongitude, destLatitude, }) => {
    const response = await fetch(`https://apis-navi.kakaomobility.com/v1/directions?origin=${originLongitude},${originLatitude}&destination=${destLongitude},${destLatitude}`, {
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
exports.directionSearchByCoordinatesHandler = directionSearchByCoordinatesHandler;
