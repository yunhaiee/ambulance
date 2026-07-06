"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.nearestEmergencyRoomsHandler = exports.nearestEmergencyRoomsSchema = void 0;
const zod_1 = require("zod");
const kakaoFetch_js_1 = require("./kakaoFetch.js");

// One deterministic call replacing the old prompt-driven pipeline:
// geocode -> ER keyword search -> multi-destination ETA -> sort by ETA.
// The LLM receives ranked JSON and only has to present it.

const KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json";
const MULTI_DEST_URL = "https://apis-navi.kakaomobility.com/v1/destinations/directions";
const SINGLE_DEST_URL = "https://apis-navi.kakaomobility.com/v1/directions";
const SEARCH_RADIUS_M = 15000; // candidate search radius (Kakao local max 20000)
const MULTI_DEST_RADIUS_M = 10000; // Kakao multi-destination API hard limit
const MAX_CANDIDATES = 30; // Kakao multi-destination API hard limit
const ER_QUERIES = ["응급실", "권역응급의료센터"];

exports.nearestEmergencyRoomsSchema = {
    location: zod_1.z.string().optional().describe("출발지 주소 또는 장소명 (예: '대전 유성구 문지로 193', '카이스트 문지캠퍼스')"),
    latitude: zod_1.z.number().optional().describe("출발지 위도 (location 대신 좌표를 알고 있는 경우)"),
    longitude: zod_1.z.number().optional().describe("출발지 경도 (location 대신 좌표를 알고 있는 경우)"),
    limit: zod_1.z.number().int().min(1).max(15).optional().describe("반환할 응급실 수 (기본 10)"),
};

const isHospital = (doc) => {
    if (doc.category_group_code === "HP8") {
        return true;
    }
    if (doc.category_group_code) {
        // Categorized as something other than a hospital (e.g. PM9 pharmacy).
        return false;
    }
    return /병원|의료원/.test(doc.place_name || "");
};

const resolveOrigin = async ({ location, latitude, longitude }) => {
    if (latitude !== undefined && longitude !== undefined) {
        return { ok: true, x: longitude, y: latitude, resolved_from: "coordinates" };
    }
    if (!location) {
        return { ok: false, error: "location 또는 latitude/longitude 중 하나는 필수입니다." };
    }
    const result = await kakaoFetch_js_1.kakaoFetchJson(`${KEYWORD_SEARCH_URL}?query=${encodeURIComponent(location)}`, { method: "GET", headers: kakaoFetch_js_1.kakaoHeaders() });
    if (!result.ok) {
        return { ok: false, error: `출발지 검색 실패: ${result.error}` };
    }
    const doc = (result.data.documents || [])[0];
    if (!doc) {
        return { ok: false, error: `출발지를 찾을 수 없습니다: ${location}` };
    }
    return { ok: true, x: Number(doc.x), y: Number(doc.y), resolved_from: doc.place_name || doc.address_name };
};

const searchCandidates = async (origin) => {
    const byId = new Map();
    const failures = [];
    for (const query of ER_QUERIES) {
        const url = `${KEYWORD_SEARCH_URL}?query=${encodeURIComponent(query)}&x=${origin.x}&y=${origin.y}&radius=${SEARCH_RADIUS_M}&sort=distance&size=15`;
        const result = await kakaoFetch_js_1.kakaoFetchJson(url, { method: "GET", headers: kakaoFetch_js_1.kakaoHeaders() });
        if (!result.ok) {
            failures.push(`후보 검색 실패 (${query}): ${result.error}`);
            continue;
        }
        for (const doc of result.data.documents || []) {
            if (isHospital(doc) && !byId.has(doc.id)) {
                byId.set(doc.id, doc);
            }
        }
    }
    return { candidates: [...byId.values()].slice(0, MAX_CANDIDATES), failures };
};

const routeMulti = async (origin, candidates) => {
    const body = {
        origin: { x: origin.x, y: origin.y },
        destinations: candidates.map((doc) => ({ key: doc.id, x: Number(doc.x), y: Number(doc.y) })),
        radius: MULTI_DEST_RADIUS_M,
        priority: "TIME",
    };
    const result = await kakaoFetch_js_1.kakaoFetchJson(MULTI_DEST_URL, {
        method: "POST",
        headers: kakaoFetch_js_1.kakaoHeaders(),
        body: JSON.stringify(body),
    });
    const routed = new Map();
    if (result.ok) {
        for (const route of result.data.routes || []) {
            if (route.result_code === 0 && route.summary) {
                routed.set(route.key, {
                    distance_m: route.summary.distance,
                    duration_s: route.summary.duration,
                    source: "multi_destination",
                });
            }
        }
    }
    return routed;
};

// Fallback for candidates the multi-destination API could not route
// (beyond its 10km radius): individual direction searches.
const routeSingles = async (origin, candidates) => {
    const routed = new Map();
    const results = await Promise.all(candidates.map(async (doc) => {
        const url = `${SINGLE_DEST_URL}?origin=${origin.x},${origin.y}&destination=${doc.x},${doc.y}&priority=TIME`;
        const result = await kakaoFetch_js_1.kakaoFetchJson(url, { method: "GET", headers: kakaoFetch_js_1.kakaoHeaders() });
        return { doc, result };
    }));
    for (const { doc, result } of results) {
        const summary = result.ok && result.data.routes && result.data.routes[0] &&
            result.data.routes[0].result_code === 0 ? result.data.routes[0].summary : null;
        if (summary) {
            routed.set(doc.id, {
                distance_m: summary.distance,
                duration_s: summary.duration,
                source: "single_destination",
            });
        }
    }
    return routed;
};

const nearestEmergencyRoomsHandler = async (params) => {
    const limit = params.limit || 10;

    const origin = await resolveOrigin(params);
    if (!origin.ok) {
        return kakaoFetch_js_1.toolError(`find_nearest_emergency_rooms: ${origin.error}`);
    }

    const { candidates, failures } = await searchCandidates(origin);
    if (candidates.length === 0) {
        return kakaoFetch_js_1.toolError(`find_nearest_emergency_rooms: 반경 ${SEARCH_RADIUS_M / 1000}km 내 응급실 후보를 찾지 못했습니다. ${failures.join("; ")}`);
    }

    const routed = await routeMulti(origin, candidates);
    const unrouted = candidates.filter((doc) => !routed.has(doc.id));
    if (unrouted.length > 0) {
        const singles = await routeSingles(origin, unrouted);
        for (const [key, value] of singles) {
            routed.set(key, value);
        }
    }

    const hospitals = candidates
        .filter((doc) => routed.has(doc.id))
        .map((doc) => {
            const route = routed.get(doc.id);
            return {
                name: doc.place_name,
                phone: doc.phone || null,
                address: doc.road_address_name || doc.address_name,
                latitude: Number(doc.y),
                longitude: Number(doc.x),
                distance_km: Math.round(route.distance_m / 100) / 10,
                eta_minutes: Math.round(route.duration_s / 60),
                route_source: route.source,
            };
        })
        // Sorted in code - ETA first (golden hour), distance as tiebreak.
        .sort((a, b) => (a.eta_minutes - b.eta_minutes) || (a.distance_km - b.distance_km))
        .slice(0, limit)
        .map((hospital, index) => ({ rank: index + 1, ...hospital }));

    const unreachable = candidates.filter((doc) => !routed.has(doc.id)).map((doc) => doc.place_name);
    return kakaoFetch_js_1.toolSuccess({
        origin: {
            latitude: origin.y,
            longitude: origin.x,
            resolved_from: origin.resolved_from,
        },
        hospitals,
        unreachable,
        warnings: failures,
        generated_at: new Date().toISOString(),
    });
};
exports.nearestEmergencyRoomsHandler = nearestEmergencyRoomsHandler;
