"use server";

import { revalidatePath } from "next/cache";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "change-me-in-production";

export type SettingsActionState = {
  ok: boolean;
  message: string;
};

async function settingsFetch(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": ADMIN_API_KEY,
      ...(init?.headers ?? {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message
          ? `${detail.message}${detail.fix ? ` ${detail.fix}` : ""}`
          : `Settings request failed: ${response.status}`;
    throw new Error(message);
  }
  return data;
}

export async function saveSettings(_state: SettingsActionState, formData: FormData): Promise<SettingsActionState> {
  const payload: Record<string, string> = {};
  for (const [key, value] of formData.entries()) {
    if (key.startsWith("$")) {
      continue;
    }
    payload[key] = String(value);
  }
  try {
    await settingsFetch("/settings", {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    revalidatePath("/settings");
    revalidatePath("/admin/settings");
    return { ok: true, message: "Settings saved. Secret fields remain masked after save." };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : "Could not save settings." };
  }
}

export async function testTicketmaster(): Promise<SettingsActionState> {
  return runTest("/settings/test-ticketmaster");
}

export async function testEventbrite(): Promise<SettingsActionState> {
  return runTest("/settings/test-eventbrite");
}

export async function testBandsintown(): Promise<SettingsActionState> {
  return runTest("/settings/test-bandsintown");
}

export async function testSongkick(): Promise<SettingsActionState> {
  return runTest("/settings/test-songkick");
}

export async function enableEventbrite(): Promise<SettingsActionState> {
  const result = await runTest("/settings/enable-eventbrite");
  if (result.ok) {
    revalidatePath("/settings");
    revalidatePath("/admin/settings");
    revalidatePath("/admin/source-settings");
  }
  return result;
}

export async function testInstagram(): Promise<SettingsActionState> {
  return runTest("/settings/test-instagram");
}

export async function testAllSettings(): Promise<SettingsActionState> {
  return runTest("/settings/test-all");
}

async function runTest(path: string): Promise<SettingsActionState> {
  try {
    const data = await settingsFetch(path, { method: "POST" });
    return { ok: Boolean(data.ok), message: data.message ?? JSON.stringify(data.checks ?? data) };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : "Connection test failed." };
  }
}
