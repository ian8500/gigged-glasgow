import { SubmitButton } from "@/components/admin/SubmitButton";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function submitEvent(formData: FormData) {
  "use server";
  await fetch(`${API_BASE_URL}/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_title: formData.get("event_title"),
      artist: formData.get("artist"),
      venue: formData.get("venue"),
      date: formData.get("date"),
      time: formData.get("time"),
      ticket_url: formData.get("ticket_url"),
      price: formData.get("price") || null,
      promoter_contact_email: formData.get("promoter_contact_email"),
      image_upload_url: formData.get("image_upload_url") || null,
      notes: formData.get("notes") || null
    })
  });
}

export default function SubmitEventPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-8">
      <section>
        <p className="font-display text-sm uppercase tracking-[0.28em] text-acid">Promoters</p>
        <h1 className="mt-2 font-display text-5xl font-black leading-none text-bone">Submit a Glasgow gig</h1>
      </section>
      <form action={submitEvent} className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-6 md:grid-cols-2">
        {[
          ["event_title", "Event title"],
          ["artist", "Artist"],
          ["venue", "Venue"],
          ["date", "Date"],
          ["time", "Time"],
          ["ticket_url", "Ticket URL"],
          ["price", "Price"],
          ["promoter_contact_email", "Promoter contact email"],
          ["image_upload_url", "Image upload URL"]
        ].map(([name, label]) => (
          <label key={name} className="grid gap-2 text-sm font-bold text-bone/70">
            {label}
            <input name={name} type={name === "date" ? "date" : name === "time" ? "time" : "text"} required={!["price", "image_upload_url"].includes(name)} className="rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
          </label>
        ))}
        <label className="grid gap-2 text-sm font-bold text-bone/70 md:col-span-2">
          Notes
          <textarea name="notes" className="min-h-28 rounded-md border border-bone/10 bg-night px-3 py-2 text-sm text-bone" />
        </label>
        <SubmitButton pendingText="Submitting" className="rounded-md bg-acid px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-ink md:col-span-2">
          Submit for review
        </SubmitButton>
      </form>
    </main>
  );
}
