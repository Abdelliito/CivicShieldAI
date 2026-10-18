import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button, Field, Modal } from "./UI";
describe("accessible operational forms", () => {
  it("names an input exactly and associates explanatory help separately", () => {
    render(
      <Field label="Description" hint="At least fifteen characters">
        <textarea required minLength={15} />
      </Field>,
    );
    const input = screen.getByRole("textbox", { name: "Description" });
    expect(input).toHaveAccessibleDescription("At least fifteen characters");
    expect(input).toBeRequired();
  });
  it("connects labels through nested password control layouts", async () => {
    render(
      <Field label="Password">
        <div>
          <input type="password" />
          <button type="button" aria-label="Show password">
            Show
          </button>
        </div>
      </Field>,
    );
    const input = screen.getByLabelText("Password", { exact: true });
    await userEvent.click(screen.getByText("Password", { exact: true }));
    expect(input).toHaveFocus();
  });
  it("disables a pending mutation button to prevent duplicate submissions", () => {
    render(<Button pending>Submit report</Button>);
    expect(
      screen.getByRole("button", { name: "Submit report" }),
    ).toBeDisabled();
  });
  it("supports closing a dialog with the keyboard", async () => {
    const close = vi.fn();
    render(
      <Modal open onClose={close} title="Review incident">
        <p>Review the response before closing.</p>
      </Modal>,
    );
    expect(
      screen.getByRole("dialog", { name: "Review incident" }),
    ).toBeVisible();
    await userEvent.keyboard("{Escape}");
    expect(close).toHaveBeenCalledOnce();
  });
});
