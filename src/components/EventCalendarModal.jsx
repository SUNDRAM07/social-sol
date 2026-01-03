import { useState, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { X, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import apiClient from "../lib/apiClient.js";

const EventCalendarModal = ({ isOpen, onClose, calendarConnected }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedView, setSelectedView] = useState("Month"); // Today, Week, Month
  const [selectedDate, setSelectedDate] = useState(null);

  // Load events when modal opens
  useEffect(() => {
    if (isOpen) {
      // Always load recent posts as events
      loadRecentPostsAsEvents();
      // Only load Google Calendar events if connected
      if (calendarConnected) {
        loadEvents();
      }
    }
  }, [isOpen, calendarConnected]);

  const loadRecentPostsAsEvents = async () => {
    try {
      const data = await apiClient.getAllPosts({ limit: 50 });
      if (data && data.success && Array.isArray(data.posts)) {
        const postEvents = data.posts
          .filter((p) => p.scheduled_at || p.scheduledAt || p.start_time || p.date)
          .map((p) => {
            const scheduledDate = p.scheduled_at || p.scheduledAt || p.start_time || p.date;
            return {
              id: `post-${p.id}`,
              title: p.campaign_name || p.campaignName || p.original_description || p.caption || "Untitled Post",
              description: p.original_description || p.caption || p.message || "",
              start: new Date(scheduledDate),
              end: new Date(new Date(scheduledDate).getTime() + 30 * 60 * 1000), // 30 minutes
              color: "#8b5cf6", // Purple for posts
            };
          });
        
        // Merge with existing events
        setEvents((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          const newPostEvents = postEvents.filter((e) => !existingIds.has(e.id));
          return [...prev, ...newPostEvents];
        });
      }
    } catch (error) {
      console.error("Failed to load recent posts as events:", error);
    }
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getGoogleUpcomingEvents();
      if (data && data.success && Array.isArray(data.events)) {
        // Transform Google Calendar events to our format
        const transformedEvents = data.events.map((ev) => ({
          id: ev.id,
          title: ev.summary || "Untitled Event",
          description: ev.description || "",
          start: ev.start ? new Date(ev.start) : new Date(),
          end: ev.end ? new Date(ev.end) : new Date(),
          color: getEventColor(ev.summary || ""),
        }));
        setEvents(transformedEvents);
      } else {
        setEvents([]);
      }
    } catch (error) {
      console.error("Failed to load events:", error);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const getEventColor = (title) => {
    // Assign colors based on event title or use default
    if (title.toLowerCase().includes("meeting")) return "#10b981"; // green
    if (title.toLowerCase().includes("trip") || title.toLowerCase().includes("travel")) return "#ef4444"; // red
    if (title.toLowerCase().includes("lunch") || title.toLowerCase().includes("dinner")) return "#3b82f6"; // blue
    return "#8b5cf6"; // purple default
  };

  // Get days in month
  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();
    
    // Adjust to start week on Monday (0 = Monday, 6 = Sunday)
    const adjustedStartingDay = (startingDayOfWeek + 6) % 7;
    
    const days = [];
    
    // Add previous month's days
    const prevMonth = new Date(year, month - 1, 0);
    const prevMonthDays = prevMonth.getDate();
    for (let i = adjustedStartingDay - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevMonthDays - i),
        isCurrentMonth: false,
      });
    }
    
    // Add current month's days
    for (let i = 1; i <= daysInMonth; i++) {
      days.push({
        date: new Date(year, month, i),
        isCurrentMonth: true,
      });
    }
    
    // Add next month's days to fill the grid
    const remainingDays = 42 - days.length; // 6 rows * 7 days
    for (let i = 1; i <= remainingDays; i++) {
      days.push({
        date: new Date(year, month + 1, i),
        isCurrentMonth: false,
      });
    }
    
    return days;
  };

  const navigateMonth = (direction) => {
    setCurrentDate((prev) => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + direction);
      return newDate;
    });
  };

  const monthName = currentDate.toLocaleString("default", { month: "long", year: "numeric" });
  const days = getDaysInMonth(currentDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Filter events based on selected view
  const filteredEvents = useMemo(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    
    if (selectedView === "Today") {
      const todayStart = new Date(now);
      const todayEnd = new Date(now);
      todayEnd.setHours(23, 59, 59, 999);
      
      return events.filter((ev) => {
        const evDate = new Date(ev.start);
        return evDate >= todayStart && evDate <= todayEnd;
      }).sort((a, b) => new Date(a.start) - new Date(b.start));
    } else if (selectedView === "Week") {
      const weekStart = new Date(now);
      weekStart.setDate(now.getDate() - now.getDay() + 1); // Monday
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      weekEnd.setHours(23, 59, 59, 999);
      
      return events.filter((ev) => {
        const evDate = new Date(ev.start);
        return evDate >= weekStart && evDate <= weekEnd;
      }).sort((a, b) => new Date(a.start) - new Date(b.start));
    } else {
      // Month view - show all events for the current month
      const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      monthEnd.setHours(23, 59, 59, 999);
      
      return events.filter((ev) => {
        const evDate = new Date(ev.start);
        return evDate >= monthStart && evDate <= monthEnd;
      }).sort((a, b) => new Date(a.start) - new Date(b.start));
    }
  }, [events, currentDate, selectedView]);

  // Get events for a specific date
  const getEventsForDate = (date) => {
    const dateStr = date.toDateString();
    return events.filter((ev) => {
      const evDate = new Date(ev.start);
      return evDate.toDateString() === dateStr;
    });
  };

  // Check if date has events
  const hasEvents = (date) => {
    return getEventsForDate(date).length > 0;
  };

  // Get event color for a date (for highlighting)
  const getDateEventColor = (date) => {
    const dateEvents = getEventsForDate(date);
    if (dateEvents.length === 0) return null;
    // Return the color of the first event, or check for multi-day events
    if (dateEvents.length === 1) {
      return dateEvents[0].color;
    }
    // If multiple events, check if they're part of a multi-day event
    const multiDayEvent = dateEvents.find((ev) => {
      const start = new Date(ev.start);
      const end = new Date(ev.end);
      return end.getTime() - start.getTime() > 24 * 60 * 60 * 1000; // More than 24 hours
    });
    if (multiDayEvent) return multiDayEvent.color;
    return dateEvents[0].color;
  };

  // Check if date is part of a multi-day event
  const isPartOfMultiDayEvent = (date) => {
    return events.some((ev) => {
      const start = new Date(ev.start);
      const end = new Date(ev.end);
      const dateStr = date.toDateString();
      const startStr = start.toDateString();
      const endStr = end.toDateString();
      const isMultiDay = end.getTime() - start.getTime() > 24 * 60 * 60 * 1000;
      return isMultiDay && dateStr >= startStr && dateStr <= endStr;
    });
  };

  // Get multi-day event for a date
  const getMultiDayEventForDate = (date) => {
    return events.find((ev) => {
      const start = new Date(ev.start);
      const end = new Date(ev.end);
      const dateStr = date.toDateString();
      const startStr = start.toDateString();
      const endStr = end.toDateString();
      const isMultiDay = end.getTime() - start.getTime() > 24 * 60 * 60 * 1000;
      return isMultiDay && dateStr >= startStr && dateStr <= endStr;
    });
  };

  // Format date for event display
  const formatEventDate = (date) => {
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const dayName = days[date.getDay()];
    const day = date.getDate();
    const month = months[date.getMonth()];
    return `${dayName} - ${day} ${month}`;
  };

  // Format time
  const formatTime = (date) => {
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
  };

  // Format date range for multi-day events
  const formatDateRange = (start, end) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    
    if (startDate.toDateString() === endDate.toDateString()) {
      return formatEventDate(startDate);
    }
    
    const startDay = startDate.getDate();
    const startMonth = months[startDate.getMonth()];
    const endDay = endDate.getDate();
    const endMonth = months[endDate.getMonth()];
    
    return `${days[startDate.getDay()]} - ${startDay} ${startMonth} to ${endDay} ${endMonth}`;
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={(e) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col relative" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Event calendar</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden flex relative">
          {/* Left Side - Calendar */}
          <div className="w-2/3 border-r border-gray-200 p-6 overflow-y-auto">
            {/* Month Navigation */}
            <div className="flex items-center justify-between mb-6">
              <button
                onClick={() => navigateMonth(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </button>
              <h3 className="text-lg font-semibold text-gray-900">{monthName}</h3>
              <button
                onClick={() => navigateMonth(1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ChevronRight className="w-5 h-5 text-gray-600" />
              </button>
            </div>

            {/* Days of Week */}
            <div className="grid grid-cols-7 gap-1 mb-2">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
                <div key={day} className="text-center text-sm font-medium text-gray-600 py-2">
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
              {days.map((day, idx) => {
                const isToday = day.date.toDateString() === today.toDateString();
                const dateEvents = getEventsForDate(day.date);
                const eventColor = getDateEventColor(day.date);
                const isSelected = selectedDate && day.date.toDateString() === selectedDate.toDateString();
                const multiDayEvent = getMultiDayEventForDate(day.date);
                const isMultiDay = multiDayEvent !== undefined;
                
                // Check if this is the start, middle, or end of a multi-day event
                let multiDayPosition = null;
                if (multiDayEvent) {
                  const start = new Date(multiDayEvent.start);
                  const end = new Date(multiDayEvent.end);
                  const dateStr = day.date.toDateString();
                  const startStr = start.toDateString();
                  const endStr = end.toDateString();
                  
                  if (dateStr === startStr && dateStr === endStr) {
                    multiDayPosition = 'single';
                  } else if (dateStr === startStr) {
                    multiDayPosition = 'start';
                  } else if (dateStr === endStr) {
                    multiDayPosition = 'end';
                  } else {
                    multiDayPosition = 'middle';
                  }
                }

                return (
                  <button
                    key={idx}
                    onClick={() => {
                      if (day.isCurrentMonth) {
                        setSelectedDate(day.date);
                      }
                    }}
                    className={`
                      aspect-square p-1 rounded text-sm transition-all relative
                      ${!day.isCurrentMonth ? "text-gray-300" : "text-gray-900"}
                      ${isToday && day.isCurrentMonth ? "bg-blue-50 font-semibold" : ""}
                      ${isSelected && day.isCurrentMonth ? "ring-2 ring-purple-500" : ""}
                      ${day.isCurrentMonth ? "hover:bg-gray-50" : ""}
                      flex items-center justify-center
                    `}
                  >
                    <span className="z-10 relative">{day.date.getDate()}</span>
                    
                    {/* Single day event - colored circle */}
                    {!isMultiDay && eventColor && day.isCurrentMonth && dateEvents.length > 0 && (
                      <div
                        className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-6 h-6 rounded-full"
                        style={{ backgroundColor: eventColor }}
                      />
                    )}
                    
                    {/* Multi-day event - horizontal rectangle */}
                    {isMultiDay && day.isCurrentMonth && multiDayEvent && (
                      <div
                        className={`
                          absolute bottom-0 left-0 right-0 h-2 rounded
                          ${multiDayPosition === 'start' ? 'rounded-l-md rounded-r-none' : ''}
                          ${multiDayPosition === 'end' ? 'rounded-r-md rounded-l-none' : ''}
                          ${multiDayPosition === 'middle' ? 'rounded-none' : ''}
                          ${multiDayPosition === 'single' ? 'rounded-md' : ''}
                        `}
                        style={{ backgroundColor: multiDayEvent.color || "#ef4444" }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Side - Event List */}
          <div className="w-1/3 p-6 overflow-y-auto bg-gray-50">
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Your events</h3>
              
              {/* View Tabs */}
              <div className="flex gap-2 mb-4 border-b border-gray-200">
                {["Today", "Week", "Month"].map((view) => (
                  <button
                    key={view}
                    onClick={() => setSelectedView(view)}
                    className={`
                      px-3 py-2 text-sm font-medium transition-colors
                      ${selectedView === view
                        ? "text-purple-600 border-b-2 border-purple-600"
                        : "text-gray-600 hover:text-gray-900"
                      }
                    `}
                  >
                    {view}
                  </button>
                ))}
              </div>
            </div>

            {/* Events List */}
            {loading ? (
              <div className="text-center text-gray-500 py-8">Loading events...</div>
            ) : filteredEvents.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p className="text-sm">No events found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredEvents.map((event) => {
                  const startDate = new Date(event.start);
                  const endDate = new Date(event.end);
                  const isMultiDay = endDate.getTime() - startDate.getTime() > 24 * 60 * 60 * 1000;
                  const eventColor = event.color || "#8b5cf6";
                  
                  // Convert hex to rgba for background with opacity
                  const hexToRgba = (hex, alpha = 0.1) => {
                    const r = parseInt(hex.slice(1, 3), 16);
                    const g = parseInt(hex.slice(3, 5), 16);
                    const b = parseInt(hex.slice(5, 7), 16);
                    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
                  };

                  return (
                    <div
                      key={event.id}
                      className="p-4 rounded-lg shadow-sm border-l-4"
                      style={{
                        borderLeftColor: eventColor,
                        borderLeftWidth: "4px",
                        backgroundColor: hexToRgba(eventColor, 0.15),
                      }}
                    >
                      <div className="text-xs text-gray-600 mb-1 font-medium">
                        {isMultiDay
                          ? formatDateRange(startDate, endDate)
                          : formatEventDate(startDate)}
                      </div>
                      <div className="text-xs text-gray-600 mb-2">
                        {formatTime(startDate)}
                      </div>
                      <div className="font-semibold text-gray-900 mb-1 text-base">
                        {event.title}
                      </div>
                      {event.description && (
                        <div className="text-sm text-gray-700 line-clamp-2 mt-1">
                          {event.description}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

          </div>
        </div>
        
        {/* Add Event Button - Fixed position at bottom right of modal */}
        <button
          className="absolute bottom-6 right-6 w-14 h-14 bg-purple-600 hover:bg-purple-700 text-white rounded-full shadow-xl flex items-center justify-center transition-colors z-10"
          title="Add new event"
          onClick={() => {
            // TODO: Implement add event functionality
            console.log("Add event clicked");
          }}
        >
          <Plus className="w-7 h-7" />
        </button>
      </div>
    </div>,
    document.body
  );
};

export default EventCalendarModal;

