import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

function CircularProgress({ progress, color }: { progress: number; color: string }) {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative w-20 h-20">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="6"
        />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-300"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold">{progress}%</span>
      </div>
    </div>
  );
}

export function CompletionProgress() {
  const { studentId, selectedCourse } = useAuth();

  const { data: progressData, isLoading } = useQuery({
    queryKey: ["progress", studentId, selectedCourse],
    queryFn: () => studentId ? api.getProgress(parseInt(studentId), selectedCourse || undefined) : Promise.resolve([]),
    enabled: !!studentId,
  });

  // Group by topic and calculate weighted average completion percentage
  const uniqueTopics = progressData ? progressData.reduce((acc: any, item: any) => {
    if (!acc[item.topic]) {
      acc[item.topic] = {
        topic: item.topic,
        totalTasks: 0,
        completedTasks: 0,
        totalWeight: 0,
        weightedSum: 0
      };
    }
    acc[item.topic].totalTasks += item.total_tasks;
    acc[item.topic].completedTasks += item.completed_tasks;
    acc[item.topic].totalWeight += item.total_tasks;
    acc[item.topic].weightedSum += (item.completion_percent * item.total_tasks);
    return acc;
  }, {}) : {};

  // Calculate final completion percentage for each topic
  Object.keys(uniqueTopics).forEach(topic => {
    const data = uniqueTopics[topic];
    data.completion_percent = data.totalWeight > 0 ? Math.round(data.weightedSum / data.totalWeight) : 0;
  });

  return (
    <Card className="flex flex-col h-96 shadow-xl shadow-blue-200/60">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Completion Progress</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4">
        {isLoading ? (
          <div className="text-center text-muted-foreground">Loading...</div>
        ) : Object.keys(uniqueTopics).length > 0 ? (
          Object.values(uniqueTopics).map((item: any) => (
            <div key={item.topic} className="flex items-center justify-between">
              <span className="text-sm font-medium flex-1">{item.topic}</span>
              <CircularProgress progress={item.completion_percent} color="hsl(var(--primary))" />
            </div>
          ))
        ) : (
          <div className="text-center text-muted-foreground">No progress data available</div>
        )}
      </CardContent>
    </Card>
  );
}
export default CompletionProgress;
