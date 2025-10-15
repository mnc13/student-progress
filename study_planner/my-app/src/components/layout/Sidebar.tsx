import { Stethoscope, Activity, Beaker, Pill, Microscope, LogOut, HeartPulse } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const subjects = [
  { name: "Anatomy", icon: HeartPulse, active: true },
  { name: "Physiology", icon: Activity, active: false },
  { name: "Biochemistry", icon: Beaker, active: false },
  { name: "Pharmacology", icon: Pill, active: false },
  { name: "Forensics", icon: Microscope, active: false, badge: 4 },
];

export function Sidebar() {
  return (
    <aside className="w-64 min-h-screen bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo */}
      <div className="p-6 flex items-center gap-2">
        <Stethoscope className="w-8 h-8 text-primary" />
        <span className="text-xl font-bold text-primary">NNdemy</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        {subjects.map((subject) => {
          const Icon = subject.icon;
          return (
            <button
              key={subject.name}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors",
                subject.active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="flex-1 text-left font-medium">{subject.name}</span>
              {subject.badge && (
                <Badge className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center p-0">
                  {subject.badge}
                </Badge>
              )}
            </button>
          );
        })}
      </nav>

      {/* Sign Out */}
      <div className="p-3">
        <button className="w-full flex items-center gap-3 px-4 py-3 text-destructive hover:bg-destructive/10 rounded-lg transition-colors">
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
export default Sidebar;