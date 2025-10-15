import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const daysOfWeek = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

export function CalendarWidget() {
  const { studentId, selectedCourse } = useAuth();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [yearInput, setYearInput] = useState("");
  const [isYearPopoverOpen, setIsYearPopoverOpen] = useState(false);

  const { data: upcomingEvents, isLoading } = useQuery({
    queryKey: ["upcomingEvents", studentId, selectedCourse],
    queryFn: () => studentId ? api.getUpcomingEvents(parseInt(studentId), selectedCourse || undefined) : Promise.resolve([]),
    enabled: !!studentId,
  });

  // Generate calendar dates for selected month
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const dates = [];
  let week = [];
  for (let i = 0; i < firstDay; i++) {
    week.push(null);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    week.push(day);
    if (week.length === 7) {
      dates.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    while (week.length < 7) {
      week.push(null);
    }
    dates.push(week);
  }

  // Highlighted dates from upcoming events and today's date
  const highlightedDates: { [key: number]: string } = {};
  const today = new Date();
  const isCurrentMonth = today.getMonth() === month && today.getFullYear() === year;
  const todayDate = today.getDate();

  // Mark today's date with blue color
  if (isCurrentMonth) {
    highlightedDates[todayDate] = "bg-blue-500 text-white font-bold";
  }

  // Mark upcoming events with pink color, but red for exam days (today's events)
  if (upcomingEvents) {
    upcomingEvents.forEach((event: any) => {
      const eventDate = new Date(event.date);
      if (eventDate.getMonth() === month && eventDate.getFullYear() === year) {
        const day = eventDate.getDate();
        const isToday = isCurrentMonth && day === todayDate;

        if (isToday) {
          // Exam day - red color takes priority
          highlightedDates[day] = "bg-red-500 text-white font-bold";
        } else {
          // Regular upcoming event - pink color
          highlightedDates[day] = "bg-pink-500 text-white font-bold";
        }
      }
    });
  }

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      if (direction === 'prev') {
        newDate.setMonth(prev.getMonth() - 1);
      } else {
        newDate.setMonth(prev.getMonth() + 1);
      }
      return newDate;
    });
  };

  const handleYearSubmit = () => {
    const year = parseInt(yearInput);
    if (year >= 1900 && year <= 2100) {
      setCurrentDate(prev => {
        const newDate = new Date(prev);
        newDate.setFullYear(year);
        return newDate;
      });
      setIsYearPopoverOpen(false);
      setYearInput("");
    }
  };

  return (
    <Card className="shadow-xl shadow-blue-200/60">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold">My Progress</CardTitle>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigateMonth('prev')}
            className="p-1 hover:bg-muted rounded"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <Popover open={isYearPopoverOpen} onOpenChange={setIsYearPopoverOpen}>
            <PopoverTrigger asChild>
              <button className="text-sm font-medium min-w-[120px] text-center hover:bg-muted rounded px-2 py-1">
                {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' }).toUpperCase()}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-48">
              <div className="space-y-2">
                <label className="text-sm font-medium">Enter Year</label>
                <Input
                  type="number"
                  placeholder="2024"
                  value={yearInput}
                  onChange={(e) => setYearInput(e.target.value)}
                  min="1900"
                  max="2100"
                />
                <Button onClick={handleYearSubmit} className="w-full">
                  Go to Year
                </Button>
              </div>
            </PopoverContent>
          </Popover>
          <button
            onClick={() => navigateMonth('next')}
            className="p-1 hover:bg-muted rounded"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* Days of week */}
          <div className="grid grid-cols-7 gap-2 mb-2">
            {daysOfWeek.map((day) => (
              <div key={day} className="text-center text-xs font-medium text-muted-foreground">
                {day}
              </div>
            ))}
          </div>

          {/* Dates */}
          {dates.map((week, weekIndex) => (
            <div key={weekIndex} className="grid grid-cols-7 gap-2">
              {week.map((date, dayIndex) => (
                <div
                  key={dayIndex}
                  className={`
                    aspect-square flex items-center justify-center text-sm rounded-lg
                    ${date ? "cursor-pointer" : ""}
                    ${date && !highlightedDates[date] ? "hover:bg-muted" : ""}
                    ${date && highlightedDates[date] ? highlightedDates[date] : ""}
                  `}
                >
                  {date}
                </div>
              ))}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default CalendarWidget;
