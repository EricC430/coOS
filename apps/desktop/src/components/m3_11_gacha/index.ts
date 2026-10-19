/**
 * M3.11 Gamification Gacha & Visual Studio Module
 * Comprehensive exports for UI, Canvas Compositor, AI Generators, and Psychological Safety
 */

export * from "./types";
export * from "./presetBackgrounds";
export * from "./presetObjects";
export * from "./promptBuilder";
export * from "./telemetry";

// User Story 1: Gacha Draw System
export { GachaDrawButton } from "./GachaDrawButton";
export type { GachaDrawButtonProps } from "./GachaDrawButton";
export { GachaResultToast } from "./GachaDrawButton/GachaResultToast";
export type { GachaResultToastProps } from "./GachaDrawButton/GachaResultToast";
export { useDrawRateLimit } from "./GachaDrawButton/useDrawRateLimit";

// User Story 2: Background Generator
export { BackgroundGenerator } from "./BackgroundGenerator";
export type { BackgroundGeneratorProps } from "./BackgroundGenerator";

// User Story 3: Object Generator
export { ObjectGenerator } from "./ObjectGenerator";
export type { ObjectGeneratorProps } from "./ObjectGenerator";

// User Story 4: Visual Studio Canvas & AI Harmonization
export { VisualStudioCanvas } from "./VisualStudioCanvas";
export type { VisualStudioCanvasProps } from "./VisualStudioCanvas";
export { CanvasViewport } from "./VisualStudioCanvas/CanvasViewport";
export type { CanvasViewportProps } from "./VisualStudioCanvas/CanvasViewport";
export { LayerControls } from "./VisualStudioCanvas/LayerControls";
export type { LayerControlsProps } from "./VisualStudioCanvas/LayerControls";
export { useCanvasCompositor } from "./VisualStudioCanvas/useCanvasCompositor";
export { useImageHarmonizer } from "./VisualStudioCanvas/useImageHarmonizer";

// User Story 5: Psychological Invariants & Hidden Achievements
export { AchievementGrid } from "./HiddenAchievement/AchievementGrid";
export type { AchievementGridProps } from "./HiddenAchievement/AchievementGrid";
export { SurpriseModal } from "./HiddenAchievement/SurpriseModal";
export type { SurpriseModalProps } from "./HiddenAchievement/SurpriseModal";
export { HiddenAchievementListener } from "./HiddenAchievement/HiddenAchievementListener";
export type { HiddenAchievementListenerProps } from "./HiddenAchievement/HiddenAchievementListener";
export { GachaPromotion } from "./GachaPromotion";
export type { GachaPromotionProps } from "./GachaPromotion";
export { DrawChallengeButton } from "./DrawChallengeButton";
export type { DrawChallengeButtonProps } from "./DrawChallengeButton";

// Integrated Hub
export { GachaStudioHub } from "./GachaStudioHub";
export type { GachaStudioHubProps } from "./GachaStudioHub";
