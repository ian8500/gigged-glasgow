import { approveSubmission, rejectSubmission } from "@/app/admin/actions";
import { AdminPageHeader } from "@/components/admin/AdminSectionNav";
import { SubmitButton } from "@/components/admin/SubmitButton";
import { getPromoterSubmissions } from "@/lib/api";

export default async function SubmissionsPage() {
  const submissions = await getPromoterSubmissions();

  return (
    <main className="space-y-8">
      <AdminPageHeader eyebrow="Review" title="Promoter submissions" />
      <section className="grid gap-4">
        {submissions.length === 0 ? (
          <div className="rounded-lg border border-dashed border-bone/20 bg-bone/[0.04] p-8 text-bone/55">No pending submissions.</div>
        ) : (
          submissions.map((submission) => (
            <div key={submission.id} className="grid gap-4 rounded-lg border border-bone/10 bg-bone/[0.04] p-5 lg:grid-cols-[1fr_220px]">
              <div>
                <h2 className="font-display text-xl font-black text-bone">{submission.event_title}</h2>
                <p className="mt-2 text-sm text-bone/62">{submission.artist} · {submission.venue} · {submission.date} {submission.time}</p>
                <p className="mt-2 break-all text-xs text-clyde">{submission.ticket_url}</p>
                <p className="mt-2 text-xs text-bone/45">{submission.promoter_contact_email}</p>
                {submission.notes ? <p className="mt-3 text-sm leading-6 text-bone/60">{submission.notes}</p> : null}
              </div>
              <div className="space-y-3">
                <SubmissionAction submissionId={submission.id} action={approveSubmission} label="Approve" />
                <SubmissionAction submissionId={submission.id} action={rejectSubmission} label="Reject" />
              </div>
            </div>
          ))
        )}
      </section>
    </main>
  );
}

function SubmissionAction({ submissionId, action, label }: { submissionId: number; action: (formData: FormData) => Promise<void>; label: string }) {
  return (
    <form action={action}>
      <input type="hidden" name="submissionId" value={submissionId} />
      <SubmitButton pendingText="Working" className="w-full rounded-md border border-bone/20 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-bone">
        {label}
      </SubmitButton>
    </form>
  );
}
