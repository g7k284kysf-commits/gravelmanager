const priorityStyles = {
  A: "bg-ink text-gravel",
  B: "bg-gravel text-ink",
  C: "bg-fog text-moss",
} as const;

export function PriorityBadge({ priority }: { priority: "A" | "B" | "C" }) {
  return (
    <span aria-label={`Race priority ${priority}`} className={`grid h-9 w-9 place-items-center rounded-full text-sm font-black ${priorityStyles[priority]}`}>
      {priority}
    </span>
  );
}
