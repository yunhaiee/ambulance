"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.directionSearchByAddressHandler = exports.directionSearchByAddressSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.directionSearchByAddressSchema = {
    originAddress: zod_1.z.string(),
    destAddress: zod_1.z.string(),
};
const directionSearchByAddressHandler = async ({ originAddress, destAddress, }) => {
    var _a, _b, _c, _d, _e, _f, _g, _h;
    const [originResult, destResult] = await Promise.all([
        (async () => {
            const response = await fetch(`https://dapi.kakao.com/v2/local/search/address?query=${originAddress}`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `KakaoAK ${process.env.KAKAO_REST_API_KEY}`,
                },
            });
            if (!response.ok) {
                throw new Error(`Kakao geocode API request failed for origin: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        })(),
        (async () => {
            const response = await fetch(`https://dapi.kakao.com/v2/local/search/address?query=${destAddress}`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `KakaoAK ${process.env.KAKAO_REST_API_KEY}`,
                },
            });
            if (!response.ok) {
                throw new Error(`Kakao geocode API request failed for destination: ${response.statusText}`);
            }
            const data = await response.json();
            return data;
        })(),
    ]);
    // Add basic error handling for geocoding results
    if (!((_b = (_a = originResult === null || originResult === void 0 ? void 0 : originResult.documents) === null || _a === void 0 ? void 0 : _a[0]) === null || _b === void 0 ? void 0 : _b.x) ||
        !((_d = (_c = originResult === null || originResult === void 0 ? void 0 : originResult.documents) === null || _c === void 0 ? void 0 : _c[0]) === null || _d === void 0 ? void 0 : _d.y) ||
        !((_f = (_e = destResult === null || destResult === void 0 ? void 0 : destResult.documents) === null || _e === void 0 ? void 0 : _e[0]) === null || _f === void 0 ? void 0 : _f.x) ||
        !((_h = (_g = destResult === null || destResult === void 0 ? void 0 : destResult.documents) === null || _g === void 0 ? void 0 : _g[0]) === null || _h === void 0 ? void 0 : _h.y)) {
        // Consider returning a more informative error structure for MCP
        return {
            content: [{
                    type: "text",
                    text: "Geocoding failed or returned incomplete data for one or both locations.",
                }],
            isError: true,
        };
    }
    const originLongitude = originResult.documents[0].x;
    const originLatitude = originResult.documents[0].y;
    const destLongitude = destResult.documents[0].x;
    const destLatitude = destResult.documents[0].y;
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
exports.directionSearchByAddressHandler = directionSearchByAddressHandler;
