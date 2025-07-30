"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.multiDestinationDirectionSearchHandler = exports.multiDestinationDirectionSearchSchema = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.multiDestinationDirectionSearchSchema = {
    origin: zod_1.z.object({
        name: zod_1.z.string().optional(),
        x: zod_1.z.number().describe("출발지 X 좌표 (경도)"),
        y: zod_1.z.number().describe("출발지 Y 좌표 (위도)"),
    }).describe("출발지 정보"),
    destinations: zod_1.z.array(zod_1.z.object({
        key: zod_1.z.string().describe("목적지 구분용 임의 문자열"),
        x: zod_1.z.number().describe("목적지 X 좌표 (경도)"),
        y: zod_1.z.number().describe("목적지 Y 좌표 (위도)"),
    })).max(30).describe("목적지 정보 배열 (최대 30개)"),
    radius: zod_1.z.number().int().max(10000).describe("길찾기 반경 (미터, 최대 10000)"),
    priority: zod_1.z.enum(["TIME", "DISTANCE"]).optional().describe("경로 탐색 우선순위 (TIME: 최단 시간, DISTANCE: 최단 경로)"),
    avoid: zod_1.z.array(zod_1.z.enum(["ferries", "toll", "motorway", "schoolzone", "uturn"])).optional().describe("경로 탐색 시 제외할 도로 옵션 배열"),
    roadevent: zod_1.z.number().int().min(0).max(2).optional().describe("도로 통제 정보 반영 옵션 (0: 전체 반영, 1: 출발/목적지 주변 미반영, 2: 전체 미반영)"),
};
const multiDestinationDirectionSearchHandler = async (params) => {
    const { origin, destinations, radius, priority, avoid, roadevent } = params;
    const requestBody = Object.assign(Object.assign(Object.assign({ origin,
        destinations,
        radius }, (priority && { priority })), (avoid && { avoid })), (roadevent !== undefined && { roadevent }));
    try {
        const response = await fetch("https://apis-navi.kakaomobility.com/v1/destinations/directions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `KakaoAK ${process.env.KAKAO_REST_API_KEY}`,
            },
            body: JSON.stringify(requestBody),
        });
        if (!response.ok) {
            const errorText = await response.text();
            console.error("Kakao API Error:", response.status, errorText);
            return {
                content: [{
                        type: "text",
                        text: `Kakao API request failed: ${response.status} ${errorText}`,
                    }],
                isError: true,
            };
        }
        const data = await response.json();
        return {
            content: [{
                    type: "text",
                    text: JSON.stringify(data),
                }],
            isError: false,
        };
    }
    catch (error) {
        console.error("Error calling Kakao Multi-Destination API:", error);
        return {
            content: [{
                    type: "text",
                    text: `An error occurred: ${error.message}`,
                }],
            isError: true,
        };
    }
};
exports.multiDestinationDirectionSearchHandler = multiDestinationDirectionSearchHandler;
