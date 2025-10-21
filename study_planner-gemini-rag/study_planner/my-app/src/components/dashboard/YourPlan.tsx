import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Image, RefreshCw } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useEffect, useRef, useState, useMemo } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function YourPlan() {
  const { studentId, selectedCourse } = useAuth();
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef<number>(0);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: tasks, isLoading, isFetching } = useQuery({
    queryKey: ["tasks", studentId, selectedCourse],
    queryFn: () =>
      studentId ? api.getTasks(parseInt(studentId), selectedCourse || undefined) : Promise.resolve([]),
    enabled: !!studentId && !!selectedCourse,
  });

  const { data: syllabusData, isLoading: syllabusLoading } = useQuery({
    queryKey: ["syllabus", selectedTopic, selectedCourse],
    queryFn: () => (selectedTopic ? api.getSyllabus(selectedCourse!, selectedTopic) : Promise.resolve(null)),
    enabled: !!selectedTopic && !!selectedCourse,
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
      await queryClient.cancelQueries({ queryKey: ["tasks", studentId, selectedCourse] });
      const previousTasks = queryClient.getQueryData(["tasks", studentId, selectedCourse]);
      queryClient.setQueryData(["tasks", studentId, selectedCourse], (old: any) => {
        if (!old) return old;
        return old.map((task: any) => (task.id === taskId ? { ...task, status } : task));
      });
      return { previousTasks };
    },
    onError: (err, { taskId, status }, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(["tasks", studentId, selectedCourse], context.previousTasks);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progress", studentId, selectedCourse] });
    },
  });

  const handleTaskUpdate = (taskId: number, status: string) => {
    if (scrollRef.current) {
      scrollPositionRef.current = scrollRef.current.scrollTop;
    }
    updateTaskMutation.mutate({ taskId, status });
  };

  const handleViewPlan = (topic: string) => {
    setSelectedTopic(topic);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTopic(null);
  };

  // Group tasks by topic
  const groupedTasks: { [key: string]: any[] } = useMemo(() => {
    const g: { [key: string]: any[] } = {};
    if (tasks) {
      tasks.forEach((task: any) => {
        const key = task.topic;
        if (!g[key]) g[key] = [];
        g[key].push(task);
      });
    }
    return g;
  }, [tasks]);

  // ---- NEW: parse Anatomy RAG context from tasks for selected topic (non-breaking) ----
  const humanAnatomyCitations = useMemo(() => {
    if (!selectedTopic || !selectedCourse) return [];
    if (selectedCourse.toLowerCase() !== "anatomy") return [];
    const topicTasks = groupedTasks[selectedTopic] || [];
    // Find first task that has a context payload
    for (const t of topicTasks) {
      const raw = t?.context;
      if (!raw) continue;
      try {
        const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
        const arr = parsed?.human_anatomy;
        if (Array.isArray(arr)) {
          // De-dup a bit by (chapter+page)
          const seen = new Set<string>();
          const dedup = [];
          for (const item of arr) {
            const k = `${item?.chapter ?? ""}::${item?.page ?? ""}`;
            if (seen.has(k)) continue;
            seen.add(k);
            dedup.push(item);
          }
          return dedup;
        }
      } catch {
        // ignore parse errors silently
      }
    }
    return [];
  }, [selectedTopic, selectedCourse, groupedTasks]);

  // Collect unique pages for display
  const uniquePages = useMemo(() => {
    const pages = humanAnatomyCitations.map((c: any) => c?.page).filter(p => p != null && p > 0);
    return [...new Set(pages)].sort((a, b) => a - b);
  }, [humanAnatomyCitations]);
  // -------------------------------------------------------------------------------------

  return (
    <Card className="flex flex-col shadow-xl shadow-blue-200/60">
      <CardHeader className="flex-shrink-0 flex items-center justify-between">
        <CardTitle className="text-base font-semibold text-left">Your Plan</CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => generatePlanMutation.mutate()}
          disabled={generatePlanMutation.isPending}
          className="ml-2"
        >
          <RefreshCw className={`h-4 w-4 ${generatePlanMutation.isPending ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent ref={scrollRef} className="overflow-y-auto max-h-[400px] space-y-4">
        {isLoading || isFetching ? (
          <div className="text-center text-muted-foreground">Loading...</div>
        ) : Object.keys(groupedTasks).length > 0 ? (
          Object.entries(groupedTasks).map(([topic, topicTasks]) => (
            <div key={topic}>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold">{topic}</h4>
                <Button variant="outline" size="sm" onClick={() => handleViewPlan(topic)} className="text-xs">
                  View Plan
                </Button>
              </div>
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

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedTopic} - Detailed Plan</DialogTitle>
          </DialogHeader>

          {syllabusLoading ? (
            <div className="text-center text-muted-foreground">Loading...</div>
          ) : syllabusData ? (
            <div className="space-y-6">
              {/* ---- NEW: Human Anatomy (RAG) section; shows only for Anatomy and only if context exists ---- */}
              {selectedCourse?.toLowerCase() === "anatomy" && uniquePages.length > 0 && (
                <Card className="mb-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
                  <h4 className="font-semibold mb-2">Gray's Anatomy</h4>
                  <Badge variant="secondary" className="mb-2">
                    Pages: {uniquePages.join(", ")}
                  </Badge>
                  <p className="text-sm text-muted-foreground">
                    For reference and better understanding, read from these pages of the book "Gray's Anatomy for Students" by Richard L. Drake, A. Wayne Vogl, and Adam W. M. Mitchell.
                  </p>
                </Card>
              )}
              {/* --------------------------------------------------------------------------- */}

              {/* Subtopics Section */}
              {syllabusData.subtopics && syllabusData.subtopics.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-2">Subtopics</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {syllabusData.subtopics.map((subtopic: string, index: number) => (
                      <li key={index}>{subtopic}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Videos Section */}
              {syllabusData.resources &&
                syllabusData.resources.filter((r: any) => r.kind === "video").length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Videos</h4>
                    <ul className="space-y-1 text-sm">
                      {syllabusData.resources
                        .filter((r: any) => r.kind === "video")
                        .map((resource: any, index: number) => (
                          <li key={index}>
                            <a
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline"
                            >
                              {resource.title}
                            </a>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}

              {/* Research Links Section */}
              <div>
                <h4 className="font-semibold mb-2">Research Links</h4>
                <ul className="space-y-1 text-sm">
                  {/* From resources with kind article */}
                  {syllabusData.resources &&
                    syllabusData.resources
                      .filter((r: any) => r.kind === "article")
                      .map((resource: any, index: number) => (
                        <li key={`article-${index}`}>
                          <a
                            href={resource.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {resource.title}
                          </a>
                        </li>
                      ))}
                  {/* From pubmed overview */}
                  {syllabusData.pubmed && syllabusData.pubmed.overview && (
                    <>
                      <li>
                        <a
                          href={syllabusData.pubmed.overview.pubmed_ui}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          PubMed Overview
                        </a>
                      </li>
                      <li>
                        <a
                          href={syllabusData.pubmed.overview.pubmed_esearch}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          PubMed ESearch
                        </a>
                      </li>
                      <li>
                        <a
                          href={syllabusData.pubmed.overview.mesh}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          MeSH Browse
                        </a>
                      </li>
                      <li>
                        <a
                          href={syllabusData.pubmed.overview.bookshelf}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          NCBI Bookshelf
                        </a>
                      </li>
                    </>
                  )}
                  {/* From pubmed angles */}
                  {syllabusData.pubmed && syllabusData.pubmed.angles && (
                    <>
                      <li>
                        <a
                          href={syllabusData.pubmed.angles.reviews}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          PubMed Reviews
                        </a>
                      </li>
                      <li>
                        <a
                          href={syllabusData.pubmed.angles.guidelines}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          PubMed Guidelines
                        </a>
                      </li>
                      <li>
                        <a
                          href={syllabusData.pubmed.angles.imaging}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          PubMed Imaging
                        </a>
                      </li>
                    </>
                  )}
                  {/* From pubmed by_subtopic */}
                  {syllabusData.pubmed &&
                    syllabusData.pubmed.by_subtopic &&
                    syllabusData.pubmed.by_subtopic.map((sub: any, index: number) => (
                      <div key={`sub-${index}`}>
                        <li>
                          <a
                            href={sub.pubmed_ui}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {sub.subtopic} - PubMed
                          </a>
                        </li>
                        <li>
                          <a
                            href={sub.pubmed_esearch}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {sub.subtopic} - PubMed ESearch
                          </a>
                        </li>
                        <li>
                          <a
                            href={sub.mesh}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {sub.subtopic} - MeSH
                          </a>
                        </li>
                      </div>
                    ))}
                  {/* From pubmed adjacent */}
                  {syllabusData.pubmed && syllabusData.pubmed.adjacent && (
                    <li>
                      <a
                        href={syllabusData.pubmed.adjacent.radiopaedia}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Radiopaedia
                      </a>
                    </li>
                  )}
                </ul>
              </div>

              {/* Documents and Papers Section */}
              {syllabusData.resources &&
                syllabusData.resources.filter((r: any) => r.kind !== "video" && r.kind !== "article").length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Documents & Papers</h4>
                    <ul className="space-y-1 text-sm">
                      {syllabusData.resources
                        .filter((r: any) => r.kind !== "video" && r.kind !== "article")
                        .map((resource: any, index: number) => (
                          <li key={index}>
                            <a
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline"
                            >
                              {resource.title} ({resource.kind})
                            </a>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
            </div>
          ) : (
            <div className="text-center text-muted-foreground">Failed to load plan details</div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
export default YourPlan;
