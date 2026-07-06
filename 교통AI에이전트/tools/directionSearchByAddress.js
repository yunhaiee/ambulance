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
const kakaoFetch_js_1 = require("./kakaoFetch.js");
const geocodeAddress = async (address) => {
    return kakaoFetch_js_1.kakaoFetchJson(`https://dapi.kakao.com/v2/local/search/address?query=${encodeURIComponent(address)}`, {
        method: "GET",
        headers: kakaoFetch_js_1.kakaoHeaders(),
    });
};
const directionSearchByAddressHandler = async ({ originAddress, destAddress, }) => {
    var _a, _b, _c, _d;
    const [originResult, destResult] = await Promise.all([
        geocodeAddress(originAddress),
        geocodeAddress(destAddress),
    ]);
    if (!originResult.ok) {
        return kakaoFetch_js_1.toolError(`direction_search_by_address failed to geocode origin: ${originResult.error}`);
    }
    if (!destResult.ok) {
        return kakaoFetch_js_1.toolError(`direction_search_by_address failed to geocode destination: ${destResult.error}`);
    }
    const originDoc = (_b = (_a = originResult.data) === null || _a === void 0 ? void 0 : _a.documents) === null || _b === void 0 ? void 0 : _b[0];
    const destDoc = (_d = (_c = destResult.data) === null || _c === void 0 ? void 0 : _c.documents) === null || _d === void 0 ? void 0 : _d[0];
    if (!(originDoc === null || originDoc === void 0 ? void 0 : originDoc.x) || !(originDoc === null || originDoc === void 0 ? void 0 : originDoc.y) || !(destDoc === null || destDoc === void 0 ? void 0 : destDoc.x) || !(destDoc === null || destDoc === void 0 ? void 0 : destDoc.y)) {
        return kakaoFetch_js_1.toolError("direction_search_by_address: geocoding returned no coordinates for one or both addresses.");
    }
    const result = await kakaoFetch_js_1.kakaoFetchJson(`https://apis-navi.kakaomobility.com/v1/directions?origin=${originDoc.x},${originDoc.y}&destination=${destDoc.x},${destDoc.y}`, {
        method: "GET",
        headers: kakaoFetch_js_1.kakaoHeaders(),
    });
    if (!result.ok) {
        return kakaoFetch_js_1.toolError(`direction_search_by_address failed: ${result.error}`);
    }
    return kakaoFetch_js_1.toolSuccess(result.data);
};
exports.directionSearchByAddressHandler = directionSearchByAddressHandler;
