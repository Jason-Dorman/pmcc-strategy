// shadcn/ui's class joiner: later Tailwind classes win over earlier ones (DEC-71).
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
