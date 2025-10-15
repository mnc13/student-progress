import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronRight, ChevronLeft, FileText, Image } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

export function UpcomingItems() {
  const { studentId, selectedCourse } = useAuth();
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  const { data: upcomingEvents, isLoading } = useQuery({
    queryKey: ["upcomingEvents", studentId, selectedCourse],
    queryFn: () => studentId ? api.getUpcomingEvents(parseInt(studentId), selectedCourse || undefined) : Promise.resolve([]),
    enabled: !!studentId,
  });

  const { data: syllabusData, isLoading: syllabusLoading } = useQuery({
    queryKey: ["syllabus", selectedTopic, selectedCourse],
    queryFn: () => selectedTopic ? api.getSyllabus(selectedCourse!, selectedTopic) : Promise.resolve(null),
    enabled: !!selectedTopic && !!selectedCourse,
  });

  const handleItemClick = (topic: string) => {
    setSelectedTopic(topic);
  };

  const handleBackClick = () => {
    setSelectedTopic(null);
  };

  if (selectedTopic) {
    return (
      <Card className="flex flex-col">
        <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handleBackClick}
              className="p-1 hover:bg-muted rounded"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <CardTitle className="text-lg font-semibold">Syllabus</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="overflow-y-auto max-h-[400px] space-y-3">
          {syllabusLoading ? (
            <div className="text-center text-muted-foreground">Loading syllabus...</div>
          ) : syllabusData ? (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">{selectedTopic}</h3>
              {syllabusData.contents && syllabusData.contents.length > 0 ? (
                syllabusData.contents.map((content: any, index: number) => (
                  <div key={index} className="p-3 bg-muted/50 rounded-lg">
                    <h4 className="font-medium mb-2">{content.title}</h4>
                    <p className="text-sm text-muted-foreground">{content.description}</p>
                  </div>
                ))
              ) : (
                <div className="text-center text-muted-foreground">No syllabus content available</div>
              )}
            </div>
          ) : (
            <div className="text-center text-muted-foreground">Failed to load syllabus</div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col shadow-xl shadow-blue-200/60">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Upcoming Items</CardTitle>
      </CardHeader>
      <CardContent className="overflow-y-auto max-h-[400px] space-y-3">
        {isLoading ? (
          <div className="text-center text-muted-foreground">Loading...</div>
        ) : upcomingEvents && upcomingEvents.length > 0 ? (
          upcomingEvents.map((event: any, index: number) => {
            const eventDate = new Date(event.date);
            const today = new Date();
            const isToday = eventDate.toDateString() === today.toDateString();
            const isExamDay = isToday; // Mark today's events as exam days

            return (
              <div
                key={event.id}
                onClick={() => handleItemClick(event.topic)}
                className={`flex items-start gap-3 p-3 rounded-xl hover:bg-muted/50 cursor-pointer transition-colors ${
                  isExamDay ? 'bg-red-50 border border-red-200' : ''
                }`}
              >
                <div
                  className={`text-white rounded-full w-12 h-12 flex flex-col items-center justify-center flex-shrink-0 ${
                    isExamDay ? 'bg-red-500' : 'bg-primary'
                  }`}
                >
                  <span className="text-lg font-bold">{eventDate.getDate()}</span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`text-xs ${isExamDay ? 'text-red-600 font-medium' : 'text-muted-foreground'} whitespace-nowrap`}>
                      Item {index + 6}
                    </span>
                    <span className={`text-xs ${isExamDay ? 'text-red-600' : 'text-muted-foreground'}`}>•</span>
                    <span className={`text-xs ${isExamDay ? 'text-red-600 font-medium' : 'text-muted-foreground'} whitespace-nowrap`}>
                      {event.date}
                    </span>
                    {isExamDay && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium whitespace-nowrap">
                        Exam Day
                      </span>
                    )}
                  </div>
                  <h4 className={`font-semibold mb-1 ${isExamDay ? 'text-red-700' : ''}`}>{event.topic}</h4>
                </div>

                <ChevronRight className={`w-5 h-5 flex-shrink-0 ${isExamDay ? 'text-red-500' : 'text-muted-foreground'}`} />
              </div>
            );
          })
        ) : (
          <div className="text-center text-muted-foreground">No upcoming events</div>
        )}
      </CardContent>
    </Card>
  );
}
export default UpcomingItems;
