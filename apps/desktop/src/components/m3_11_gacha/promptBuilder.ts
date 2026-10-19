/**
 * Modern FLUX/SDXL-style Prompt Builder for M3.11
 * strictly complies with Clarification Q4:
 * Discards fragmented comma tags (e.g. "8k, masterpiece, award winning")
 * and constructs coherent, descriptive, full natural-language sentences.
 */

export type BackgroundStyle =
  | "cyberpunk"
  | "zen"
  | "scifi"
  | "nature"
  | "minimalist"
  | "fantasy";

const STYLE_TEMPLATES: Record<BackgroundStyle, (scene: string) => string> = {
  cyberpunk: (scene) =>
    `A cinematic cyberpunk scene depicting ${scene}, characterized by vibrant neon cyan and magenta illumination reflected across rain-streaked surfaces, deep volumetric atmospheric haze, and intricate perspective with a shallow depth of field.`,
  zen: (scene) =>
    `A tranquil Japanese-inspired environment capturing ${scene}, characterized by natural weathered wood and stone textures, gentle diffuse morning sunlight filtering through bamboo leaves, balanced negative space, and peaceful organic harmony.`,
  scifi: (scene) =>
    `A sleek futuristic science fiction environment illustrating ${scene}, featuring clean geometric architectural lines, soft luminous ambient glow panels, matte carbon composite textures, and an expansive cinematic perspective.`,
  nature: (scene) =>
    `A breathtaking pristine natural vista capturing ${scene}, bathed in golden hour directional sunlight, featuring lush organic foliage details, serene sky gradients, and crystal-clear atmospheric clarity.`,
  minimalist: (scene) =>
    `A modern Scandinavian minimalist interior framing ${scene}, characterized by warm natural oak surfaces, delicate venetian blind shadow play across clean neutral walls, and an uncluttered spacious composition.`,
  fantasy: (scene) =>
    `An ethereal magical fantasy realm portraying ${scene}, illuminated by gentle bioluminescent flora and twilight auroras, mystical celestial dust, and an enchanting panoramic vista.`,
};

export function buildBackgroundPrompt(
  sceneDescription: string,
  style: BackgroundStyle = "cyberpunk"
): string {
  const cleanDescription = sceneDescription.trim() || "an inspiring creative workspace";
  const formatter = STYLE_TEMPLATES[style] || STYLE_TEMPLATES.cyberpunk;
  return formatter(cleanDescription);
}

export function buildObjectPrompt(
  semanticFeatures: string,
  category: "badge" | "prop" = "prop"
): string {
  const cleanFeatures = semanticFeatures.trim() || "a mysterious glowing artifact";
  const itemType = category === "badge" ? "honorary emblem badge" : "decorative tabletop item";

  return `A standalone ${itemType} portraying ${cleanFeatures}, centered in frame, sharply defined crisp contours, high quality studio key lighting with realistic reflections, rendered with a pure clean edge and completely isolated on an empty transparent alpha cutout with zero background clutter.`;
}
