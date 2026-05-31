"use client";

import { useFormStatus } from "react-dom";

type SubmitButtonProps = {
  children: React.ReactNode;
  pendingText?: string;
  className: string;
  disabled?: boolean;
};

export function SubmitButton({ children, pendingText = "Working", className, disabled }: SubmitButtonProps) {
  const { pending } = useFormStatus();

  return (
    <button disabled={disabled || pending} className={`${className} disabled:cursor-not-allowed disabled:opacity-55`}>
      {pending ? pendingText : children}
    </button>
  );
}
