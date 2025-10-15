import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronRight, FileText, Image } from "lucide-react";

const items = [
  {
    id: 6,
    date: 8,
    color: "bg-primary",
    title: "Item 6",
    time: "10th July 2021 • 8 A.M - 9 A.M",
    location: "Editing Tutorial College, Blk 56, Lagos State",
    files: ["First Chapter of Project .doc"],
  },
  {
    id: 7,
    date: 13,
    color: "bg-danger",
    title: "Item 7",
    time: "12th July 2021 • 8 A.M - 9 A.M",
    location: "School Hall, University Road, Lagos State",
    files: ["Image .jpg", "form .jpg", "Image 2 .jpg"],
  },
  {
    id: 8,
    date: 18,
    color: "bg-success",
    title: "Item 8",
    time: "18th July 2021 • 8 A.M - 9 A.M",
    location: "To be submitted via Email",
  },
  {
    id: 9,
    date: 23,
    color: "bg-warning",
    title: "Item 9",
    time: "23rd July 2021 • 10 A.M - 1 P.M",
    location: "Editing Tutorial College, Blk 56, Lagos State",
  },
];

export function UpcomingItems() {
  return (
    <Card className="flex flex-col">
      <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold">Upcoming Items</CardTitle>
        <button className="text-sm text-primary hover:underline">See all</button>
      </CardHeader>
      <CardContent className="overflow-y-auto max-h-[400px] space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-start gap-3 p-3 rounded-xl hover:bg-muted/50 cursor-pointer transition-colors"
          >
            <div
              className={`${item.color} text-white rounded-full w-12 h-12 flex flex-col items-center justify-center flex-shrink-0`}
            >
              <span className="text-lg font-bold">{item.date}</span>
            </div>

            <div className="flex-1 min-w-0">
              <h4 className="font-semibold mb-1">{item.title}</h4>
              <p className="text-xs text-muted-foreground mb-1">{item.time}</p>
              <p className="text-xs text-muted-foreground">{item.location}</p>
              
              {item.files && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {item.files.map((file, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="text-xs gap-1 bg-background"
                    >
                      {file.includes("Image") ? (
                        <Image className="w-3 h-3" />
                      ) : (
                        <FileText className="w-3 h-3" />
                      )}
                      {file}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
export default UpcomingItems;