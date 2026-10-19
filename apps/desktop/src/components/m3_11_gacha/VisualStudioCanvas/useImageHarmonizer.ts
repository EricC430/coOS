import { useState, useCallback } from "react";
import { HarmonizeRequest, HarmonizeResult } from "../types";

export interface UseImageHarmonizerOptions {
  customHarmonizeFn?: (request: HarmonizeRequest) => Promise<HarmonizeResult>;
  timeoutMs?: number;
}

export function useImageHarmonizer(options: UseImageHarmonizerOptions = {}) {
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<HarmonizeResult | null>(null);
  const [fallbackActive, setFallbackActive] = useState(false);

  const timeoutMs = options.timeoutMs || 10000;

  const harmonize = useCallback(
    async (request: HarmonizeRequest): Promise<HarmonizeResult> => {
      setLoading(true);
      setFallbackActive(false);

      // If a custom harmonizer is injected (e.g. unit tests or backend service)
      if (options.customHarmonizeFn) {
        try {
          const res = await options.customHarmonizeFn(request);
          setLastResult(res);
          setFallbackActive(res.is_fallback);
          setLoading(false);
          return res;
        } catch {
          // Graceful degradation on custom fn throw
          const fallbackRes: HarmonizeResult = {
            image_url: request.base64_draft,
            is_fallback: true,
            provider: "canvas_2d_fallback",
          };
          setLastResult(fallbackRes);
          setFallbackActive(true);
          setLoading(false);
          return fallbackRes;
        }
      }

      // Default implementation: Free Pollinations.ai or Canvas 2D Fallback
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const promptText = encodeURIComponent(
          `Photorealistic high quality harmonious blending of objects with background, ${
            request.scene_description || "digital workspace scene"
          }, ${request.objects_summary || "placed objects"}, natural light casting soft directional shadows and reflections, 8k resolution cinematic look`
        );

        // Pollinations free image gen URL
        const endpointUrl = `https://image.pollinations.ai/prompt/${promptText}?width=800&height=500&nologo=true&seed=${Math.floor(
          Math.random() * 100000
        )}`;

        const response = await fetch(endpointUrl, {
          signal: controller.signal,
          method: "GET",
        });

        clearTimeout(timer);

        if (!response.ok) {
          throw new Error(`Public AI endpoint responded with ${response.status}`);
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);

        const result: HarmonizeResult = {
          image_url: objectUrl,
          is_fallback: false,
          provider: "pollinations",
        };

        setLastResult(result);
        setLoading(false);
        return result;
      } catch {
        clearTimeout(timer);

        // 100% Graceful Fallback to 2D Canvas Draft
        const fallbackResult: HarmonizeResult = {
          image_url: request.base64_draft,
          is_fallback: true,
          provider: "canvas_2d_fallback",
        };

        setLastResult(fallbackResult);
        setFallbackActive(true);
        setLoading(false);
        return fallbackResult;
      }
    },
    [options, timeoutMs]
  );

  return {
    harmonize,
    loading,
    lastResult,
    fallbackActive,
  };
}
