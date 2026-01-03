import { useState, useEffect, useMemo } from "react";
import { Calendar as BigCalendar, momentLocalizer } from "react-big-calendar";
import moment from "moment";
import "react-big-calendar/lib/css/react-big-calendar.css";
import Modal from "./ui/Modal.jsx";
import Button from "./ui/Button.jsx";
import Input from "./ui/Input.jsx";
import Textarea from "./ui/Textarea.jsx";
import { toast } from "sonner";
import apiClient from "../lib/apiClient.js";
import { apiFetch, apiUrl } from "../lib/api.js";

const localizer = momentLocalizer(moment);

const Calendar = (props) => {
  const {
    events = [],
    onEventCreate,
    onEventUpdate,
    onEventDelete,
    onEventSelect,
    editable = true,
    height = 600,
    autoLoad = true,
  } = props;

  // 🔹 State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    start: new Date(),
    end: new Date(),
    color: "#3174ad",
    allDay: false,
    location: "",
    reminder: 15,
  });
  const [backendEvents, setBackendEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [currentView, setCurrentView] = useState("week");

  // 🔹 Load events
  const loadEvents = async () => {
    if (!autoLoad) return;
    try {
      setLoadingEvents(true);
      console.log("Loading calendar events...");
      const data = await apiClient.getCalendarEvents();
      console.log("Calendar events response:", data);
      if (data?.success && Array.isArray(data.events)) {
        setBackendEvents(data.events);
        console.log("Set backend events:", data.events);
      } else {
        console.log("No events found or invalid response");
      }
    } catch (e) {
      console.error("Failed to load calendar events:", e);
    } finally {
      setLoadingEvents(false);
    }
  };
  useEffect(() => {
    loadEvents();
  }, [events]);

  // 🔹 Styling for events
  const eventStyleGetter = (event) => ({
    style: {
      backgroundColor: event.color || "#2563eb",
      borderRadius: "8px",
      color: "#fff",
      border: "none",
      fontSize: "12px",
      fontWeight: "500",
      padding: "2px 6px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
    },
  });

  // 🔹 Prepare events
  const calendarEvents = useMemo(() => {
    // If events prop is passed (even if empty), use it. Only fallback to backendEvents if no events prop provided.
    const eventsToUse = props.events !== undefined ? events : backendEvents;
    console.log("Processing calendar events:", { 
      propsEventsDefined: props.events !== undefined, 
      events: events.length, 
      backendEvents: backendEvents.length, 
      eventsToUse: eventsToUse.length 
    });
    
    const processedEvents = eventsToUse.map((event) => ({
      ...event,
      start: new Date(event.start_time || event.start),
      end: new Date(event.end_time || event.end),
      title: event.title || "Untitled Event",
      imageUrl:
        event.imageUrl ||
        event.image_url ||
        event.driveImageUrl ||
        event.image,
      caption:
        event.generatedContent || event.caption || event.description,
      platforms: Array.isArray(event.platforms)
        ? event.platforms
        : event.platform
          ? [event.platform]
          : (event.metadata?.platforms || []),
    }));
    console.log("Processed calendar events:", processedEvents);
    return processedEvents;
  }, [events, backendEvents, props.events]);

  // 🔹 Toolbar
  const CustomToolbar = ({ label, onNavigate, onView }) => (
    <div className="flex items-center justify-between mb-4 p-4 bg-white border rounded-xl shadow-sm">
      <div className="flex items-center gap-2">
        <Button size="sm" variant="secondary" onClick={() => onNavigate("PREV")}>
          ← Prev
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onNavigate("TODAY")}>
          Today
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onNavigate("NEXT")}>
          Next →
        </Button>
      </div>
      <h2 className="text-lg font-semibold text-gray-800">{label}</h2>
      <div className="flex items-center gap-1">
        {["month", "week", "day", "agenda"].map((view) => (
          <Button
            key={view}
            size="sm"
            variant={currentView === view ? "primary" : "secondary"}
            onClick={() => {
              setCurrentView(view);
              onView(view);
            }}
            className="capitalize"
          >
            {view}
          </Button>
        ))}
      </div>
    </div>
  );

  // 🔹 Event Card (inside calendar cells)
  const EventContent = ({ event }) => (
    <div className="flex items-center gap-1 truncate">
      {event.imageUrl && (
        <img
          src={event.imageUrl}
          alt="thumb"
          className="w-4 h-4 rounded object-cover"
        />
      )}
      <span className="truncate">{event.title}</span>
    </div>
  );

  return (
    <div className="bg-gray-50 p-5 rounded-2xl shadow-lg">
      <style jsx>{`
        .rbc-calendar {
          font-family: 'Inter', sans-serif;
        }
        .rbc-toolbar {
          display: none !important;
        }
        .rbc-event {
          transition: transform 0.1s ease-in-out;
        }
        .rbc-event:hover {
          transform: scale(1.03);
        }
        .rbc-today {
          background-color: #eff6ff;
        }
        .rbc-current-time-indicator {
          background-color: #ef4444;
          height: 2px;
        }
        .rbc-time-view {
          overflow-y: auto !important;
          max-height: 100% !important;
        }
        .rbc-time-content {
          overflow-y: auto !important;
        }
        .rbc-time-view .rbc-time-gutter,
        .rbc-time-view .rbc-time-content {
          height: auto !important;
        }
        /* Force calendar to show extended hours */
        .rbc-time-content > * {
          min-height: 1200px !important; /* Extend height to show more time slots */
        }
        .rbc-time-gutter {
          min-height: 1200px !important;
        }
      `}</style>

      <BigCalendar
        localizer={localizer}
        events={calendarEvents}
        startAccessor="start"
        endAccessor="end"
        style={{ height }}
        selectable={editable}
        onSelectSlot={() => { }}
        onSelectEvent={onEventSelect}
        eventPropGetter={eventStyleGetter}
        components={{
          toolbar: CustomToolbar,
          event: EventContent,
        }}
        step={30}
        timeslots={2}
        view={currentView}
        onView={(view) => setCurrentView(view)}
        views={["month", "week", "day", "agenda"]}
        popup
        showMultiDayTimes
        min={new Date(1970, 1, 1, 0, 0, 0)} // Start at midnight
        max={new Date(1970, 1, 1, 23, 59, 59)} // End at 11:59 PM
      />

      {/* 🔹 Your Modal stays the same (logic untouched) */}
      <Modal open={isModalOpen} onOpenChange={() => setIsModalOpen(false)} title="Event">
        {/* Form code same as your version */}
      </Modal>
    </div>
  );
};

export default Calendar;