/**
 * M3.7 -- Community UI tests (MVP stub verification only)
 * Full feature tests deferred to Phase 6b.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CommunityUI } from "../../src/components/m3_7_community";

describe("M3.7 MVP Stub", () => {
  it("renders stub card without errors", () => {
    render(<CommunityUI stubMode={true} />);
    expect(screen.getByTestId("community-stub")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("stub mode does NOT render any interactive elements (no M4.13/M6.6 deps)", () => {
    render(<CommunityUI stubMode={true} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByTestId("posts-feed")).not.toBeInTheDocument();
  });
});
