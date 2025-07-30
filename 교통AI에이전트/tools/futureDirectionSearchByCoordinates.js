"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.futureDirectionSearchByCoordinatesHandler = exports.futureDirectionSearchByCoordinatesSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.futureDirectionSearchByCoordinatesSchema = {
    originLatitude: zod_1.z.number(),
    originLongitude: zod_1.z.number(),
    destinationLatitude: zod_1.z.number(),
    destinationLongitude: zod_1.z.number(),
    departureTime: zod_1.z.string(),
    waypoints: zod_1.z.string().optional(),
    priority: zod_1.z.enum(["RECOMMEND", "TIME", "DISTANCE"]).optional(),
    avoid: zod_1.z.string().optional(),
    roadEvent: zod_1.z.number().optional(),
    alternatives: zod_1.z.boolean().optional(),
    roadDetails: zod_1.z.boolean().optional(),
    carType: zod_1.z.number().optional(),
    carFuel: zod_1.z.enum(["GASOLINE", "DIESEL", "LPG"]).optional(),
    carHipass: zod_1.z.boolean().optional(),
    summary: zod_1.z.boolean().optional(),
};
const futureDirectionSearchByCoordinatesHandler = async ({ originLatitude, originLongitude, destinationLatitude, destinationLongitude, departureTime, waypoints, priority, avoid, roadEvent, alternatives, roadDetails, carType, carFuel, carHipass, summary, }) => {
    let url = `https://apis-navi.kakaomobility.com/v1/future/directions?origin=${originLongitude},${originLatitude}&destination=${destinationLongitude},${destinationLatitude}&departure_time=${departureTime}`;
    if (waypoints)
        url += `&waypoints=${waypoints}`;
    if (priority)
        url += `&priority=${priority}`;
    if (avoid)
        url += `&avoid=${avoid}`;
    if (roadEvent !== undefined)
        url += `&roadevent=${roadEvent}`;
    if (alternatives !== undefined)
        url += `&alternatives=${alternatives}`;
    if (roadDetails !== undefined)
        url += `&road_details=${roadDetails}`;
    if (carType !== undefined)
        url += `&car_type=${carType}`;
    if (carFuel)
        url += `&car_fuel=${carFuel}`;
    if (carHipass !== undefined)
        url += `&car_hipass=${carHipass}`;
    if (summary !== undefined)
        url += `&summary=${summary}`;
    const response = await fetch(url, {
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
exports.futureDirectionSearchByCoordinatesHandler = futureDirectionSearchByCoordinatesHandler;
