import { useEffect, useState } from "react";
import { Stethoscope, Activity, Beaker, Pill, Microscope, LogOut, HeartPulse } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

const subjectIcons = {
  Anatomy: HeartPulse,
  Physiology: Activity,
  Biochemistry: Beaker,
  Pharmacology: Pill,
  "Forensic Medicine": Microscope,
  Forensics: Microscope,
};

export function Sidebar() {
  const { studentId, selectedCourse, setSelectedCourse, logout } = useAuth();
  const [courses, setCourses] = useState<string[]>([]);

  const { data: coursesData, isLoading } = useQuery({
    queryKey: ["courses", studentId],
    queryFn: () => studentId ? api.getCourses(parseInt(studentId)) : Promise.resolve([]),
    enabled: !!studentId,
  });

  useEffect(() => {
    if (coursesData) {
      setCourses(coursesData.map((c: any) => c.course));
      if (!selectedCourse && coursesData.length > 0) {
        setSelectedCourse(coursesData[0].course);
      }
    }
  }, [coursesData, selectedCourse, setSelectedCourse]);

  const handleCourseSelect = (course: string) => {
    setSelectedCourse(course);
    // Invalidate queries to refresh data for the new course
    // This will be handled by React Query's query invalidation
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <aside className="w-64 min-h-screen bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo */}
      <div className="p-6 flex items-center gap-2">
        <Stethoscope className="w-8 h-8 text-primary" />
        <span className="text-xl font-bold text-primary">NNdemy</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        {isLoading ? (
          <div className="text-center text-muted-foreground">Loading courses...</div>
        ) : (
          courses.map((course) => {
            const Icon = subjectIcons[course as keyof typeof subjectIcons] || Stethoscope;
            return (
              <button
                key={course}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors",
                  selectedCourse === course
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                )}
                onClick={() => handleCourseSelect(course)}
              >
                <Icon className="w-5 h-5" />
                <span className="flex-1 text-left font-medium">{course}</span>
              </button>
            );
          })
        )}
      </nav>

      {/* Sign Out */}
      <div className="p-3">
        <button
          className="w-full flex items-center gap-3 px-4 py-3 text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
          onClick={handleLogout}
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
export default Sidebar;
