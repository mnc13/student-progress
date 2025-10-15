import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronDown } from "lucide-react";

const daysOfWeek = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const dates = [
  [null, null, null, null, null, 1, 2],
  [3, 4, 5, 6, 7, 8, 9],
  [10, 11, 12, 13, 14, 15, 16],
  [17, 18, 19, 20, 21, 22, 23],
  [24, 25, 26, 27, 28, 29, 30],
  [31, null, null, null, null, null, null],
];

// Highlighted dates with their colors
const highlightedDates: { [key: number]: string } = {
  8: "bg-primary text-primary-foreground",
  13: "bg-danger text-white",
  18: "bg-success text-white",
  23: "bg-warning text-white",
};

export function CalendarWidget() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold">My Progress</CardTitle>
        <button className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          JULY 2021 <ChevronDown className="w-4 h-4" />
        </button>
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
