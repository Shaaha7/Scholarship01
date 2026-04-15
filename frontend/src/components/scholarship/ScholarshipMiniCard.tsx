import { Calendar, IndianRupee, ExternalLink } from "lucide-react";
import { format, differenceInDays } from "date-fns";

interface Props { scholarship: any; }

export function ScholarshipMiniCard({ scholarship: s }: Props) {
  const daysLeft = s.deadline ? differenceInDays(new Date(s.deadline), new Date()) : null;
  const isUrgent = daysLeft !== null && daysLeft <= 30 && daysLeft >= 0;

  return (
    <div className={"rounded-xl border p-3 bg-card hover:shadow-md transition-all text-xs " + (isUrgent ? "border-orange-300 bg-orange-50" : "border-border")}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={"px-2 py-0.5 rounded-full text-xs font-medium badge-" + s.category}>{s.category}</span>
            {isUrgent && <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 border border-orange-200 text-xs font-medium">{daysLeft}d left!</span>}
          </div>
          <p className="font-medium text-foreground text-sm truncate">{s.title}</p>
          <p className="text-muted-foreground truncate">{s.provider}</p>
        </div>
        {s.application_url && (
          <a href={s.application_url} target="_blank" rel="noopener noreferrer"
            className="flex-shrink-0 text-blue-700 hover:text-blue-900 p-1 rounded hover:bg-blue-50">
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
      <div className="flex items-center gap-3 mt-2 text-muted-foreground">
        {s.amount && (
          <span className="flex items-center gap-1">
            <IndianRupee className="w-3 h-3" />{s.amount.toLocaleString("en-IN")}/yr
          </span>
        )}
        {s.deadline && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />{format(new Date(s.deadline), "dd MMM yyyy")}
          </span>
        )}
      </div>
    </div>
  );
}
