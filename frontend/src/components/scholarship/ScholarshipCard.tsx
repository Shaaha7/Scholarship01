import { Calendar, IndianRupee, ExternalLink, Bell, Bookmark } from "lucide-react";
import { format, differenceInDays } from "date-fns";
import Link from "next/link";

interface Props { scholarship: any; }

export function ScholarshipCard({ scholarship: s }: Props) {
  const daysLeft = s.deadline ? differenceInDays(new Date(s.deadline), new Date()) : null;
  const isUrgent = daysLeft !== null && daysLeft <= 30 && daysLeft >= 0;

  return (
    <div className={"scholarship-card group " + (isUrgent ? "border-orange-200" : "")}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex flex-wrap gap-1.5">
          <span className={"px-2.5 py-1 rounded-full text-xs font-semibold badge-" + s.category}>{s.category}</span>
          {isUrgent && <span className="px-2.5 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-semibold border border-orange-200 animate-pulse-slow">🔔 {daysLeft}d left</span>}
          {s.is_renewable && <span className="px-2.5 py-1 rounded-full bg-green-50 text-green-700 text-xs border border-green-200">Renewable</span>}
        </div>
      </div>
      <h3 className="font-display font-semibold text-foreground text-sm leading-tight mb-1 line-clamp-2">{s.title}</h3>
      <p className="text-xs text-muted-foreground mb-3">{s.provider}</p>
      <p className="text-xs text-muted-foreground line-clamp-2 mb-4">{s.description}</p>
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-4">
        {s.amount && (
          <span className="flex items-center gap-1 text-green-700 font-medium">
            <IndianRupee className="w-3 h-3" />
            {s.amount.toLocaleString("en-IN")}<span className="text-muted-foreground font-normal">/yr</span>
          </span>
        )}
        {s.deadline && (
          <span className={"flex items-center gap-1 " + (isUrgent ? "text-orange-600 font-medium" : "")}>
            <Calendar className="w-3 h-3" />{format(new Date(s.deadline), "dd MMM yyyy")}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 pt-3 border-t border-border">
        {s.application_url && (
          <a href={s.application_url} target="_blank" rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 bg-blue-700 text-white text-xs py-2 rounded-lg hover:bg-blue-800 transition-colors">
            <ExternalLink className="w-3 h-3" />Apply Now
          </a>
        )}
        <button className="flex items-center justify-center gap-1.5 border border-border text-xs py-2 px-3 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Bookmark className="w-3 h-3" />Save
        </button>
        <button className="flex items-center justify-center gap-1.5 border border-border text-xs py-2 px-3 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Bell className="w-3 h-3" />Remind
        </button>
      </div>
    </div>
  );
}
