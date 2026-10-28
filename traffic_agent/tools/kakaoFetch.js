"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.toolError = exports.toolSuccess = exports.kakaoFetchJson = exports.kakaoHeaders = void 0;

const TIMEOUT_MS = 5000;
const RETRY_DELAY_MS = 500;
const MAX_ATTEMPTS = 2;

const kakaoHeaders = () => ({
    "Content-Type": "application/json",
    Authorization: `KakaoAK ${process.env.KAKAO_REST_API_KEY}`,
});
exports.kakaoHeaders = kakaoHeaders;

/**
 * Fetch a Kakao API endpoint with a timeout and one retry on transient
 * failures (network error, timeout, 429, 5xx).
 * Returns { ok: true, data } or { ok: false, error } — never throws.
 */
const kakaoFetchJson = async (url, options = {}) => {
    if (!process.env.KAKAO_REST_API_KEY) {
        return { ok: false, error: "KAKAO_REST_API_KEY is not set" };
    }
    let lastError = "unknown error";
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        if (attempt > 1) {
            await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
        }
        let response;
        try {
            response = await fetch(url, {
                ...options,
                signal: AbortSignal.timeout(TIMEOUT_MS),
            });
        }
        catch (error) {
            lastError = error && error.name === "TimeoutError"
                ? `request timed out after ${TIMEOUT_MS}ms`
                : `request failed: ${error.message}`;
            continue;
        }
        if (response.ok) {
            try {
                return { ok: true, data: await response.json() };
            }
            catch (error) {
                lastError = `invalid JSON in response: ${error.message}`;
                continue;
            }
        }
        const body = await response.text().catch(() => "");
        lastError = `HTTP ${response.status}: ${body.slice(0, 500)}`;
        if (response.status !== 429 && response.status < 500) {
            break;
        }
    }
    return { ok: false, error: lastError };
};
exports.kakaoFetchJson = kakaoFetchJson;

const toolSuccess = (data) => ({
    content: [{ type: "text", text: JSON.stringify(data) }],
    isError: false,
});
exports.toolSuccess = toolSuccess;

const toolError = (message) => {
    console.error(message);
    return {
        content: [{ type: "text", text: `ERROR: ${message}` }],
        isError: true,
    };
};
exports.toolError = toolError;
