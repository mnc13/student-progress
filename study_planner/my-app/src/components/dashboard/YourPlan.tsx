import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Image } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useEffect, useRef } from "react";

export function YourPlan() {
  const { studentId, selectedCourse } = useAuth();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef<number>(0);

  const { data: tasks, isLoading, isFetching } = useQuery({
    queryKey: ["tasks", studentId, selectedCourse],
    queryFn: () => studentId ? api.getTasks(parseInt(studentId), selectedCourse || undefined) : Promise.resolve([]),
    enabled: !!studentId && !!selectedCourse,
  });

  const generatePlanMutation = useMutation({
    mutationFn: () => api.generatePlan(parseInt(studentId!), selectedCourse!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", studentId, selectedCourse] });
    },
  });

  // Auto-generate plan if no tasks exist for the selected course
  useEffect(() => {
    if (studentId && selectedCourse && !isLoading && !isFetching && !generatePlanMutation.isPending) {
      // Only generate if we have data and it's empty, or if query completed with no data
      const shouldGenerate = !tasks || (Array.isArray(tasks) && tasks.length === 0);
      if (shouldGenerate) {
        generatePlanMutation.mutate();
      }
    }
  }, [studentId, selectedCourse, tasks, isLoading, isFetching, generatePlanMutation]);

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: string }) =>
      api.updateTask(parseInt(studentId!), taskId, { status }),
    onMutate: async ({ taskId, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["tasks", studentId, selectedCourse] });

      // Snapshot the previous value
      const previousTasks = queryClient.getQueryData(["tasks", studentId, selectedCourse]);

      // Optimistically update to the new value
      queryClient.setQueryData(["tasks", studentId, selectedCourse], (old: any) => {
        if (!old) return old;
        return old.map((task: any) =>
          task.id === taskId ? { ...task, status } : task
        );
      });

      // Return a context object with the snapshotted value
      return { previousTasks };
    },
    onError: (err, { taskId, status }, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousTasks) {
        queryClient.setQueryData(["tasks", studentId, selectedCourse], context.previousTasks);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progress", studentId, selectedCourse] });
    },
  });

  const handleTaskUpdate = (taskId: number, status: string) => {
    // Store current scroll position before mutation
    if (scrollRef.current) {
      scrollPositionRef.current = scrollRef.current.scrollTop;
    }
    updateTaskMutation.mutate({ taskId, status });
  };

  // Group tasks by topic
  const groupedTasks: { [key: string]: any[] } = {};
  if (tasks) {
    tasks.forEach((task: any) => {
      const key = task.topic;
      if (!groupedTasks[key]) groupedTasks[key] = [];
      groupedTasks[key].push(task);
    });
  }

  return (
    <Card className="flex flex-col shadow-xl shadow-blue-200/60">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Your Plan</CardTitle>
      </CardHeader>
      <CardContent ref={scrollRef} className="overflow-y-auto max-h-[400px] space-y-4">
        {(isLoading || isFetching) ? (
          <div className="text-center text-muted-foreground">Loading...</div>
        ) : Object.keys(groupedTasks).length > 0 ? (
          Object.entries(groupedTasks).map(([topic, topicTasks]) => (
            <div key={topic}>
              <h4 className="font-semibold mb-2">{topic}</h4>
              {topicTasks.map((task: any) => (
                <div key={task.id} className="flex items-start gap-3 mb-3">
                  <input
                    type="checkbox"
                    checked={task.status === "done"}
                    onChange={(e) => handleTaskUpdate(task.id, e.target.checked ? "done" : "not_started")}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h5 className="font-medium">{task.title}</h5>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">{task.due_date}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">Hours: {task.hours}</p>
                  </div>
                </div>
              ))}
            </div>
          ))
        ) : (
          <div className="text-center text-muted-foreground">No plan available.</div>
        )}
      </CardContent>
    </Card>
  );
}
export default YourPlan;
