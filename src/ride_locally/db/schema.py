import enum
from datetime import date, datetime, time
from typing import TypeAlias, final

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Status(enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


ScrapeStatus: TypeAlias = Status
ProcessStatus: TypeAlias = Status


@final
class ScrTargetTable(Base):
    """
    Target to run scraper against.
    The scraper will run against the `url` value on periodic interval defined in `schedule_cron`
    and produce output in `scr_runs` (scraper runs) table.
    """

    __tablename__ = "scr_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True),
                                              nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # next wall-clock instant this target is eligible to run.
    # computed from schedule_cron on insert and on release. set to now() for "run now".
    # NULL = not scheduled, never claimed.
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # populated while a worker holds the row. NULL = free to claim.
    # claimed_by is hostname:pid, kept for observability + the reaper.
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    carrier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("carriers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# runs appear every time a scrape is performed and are later claimed by processor
@final
class ScrRunTable(Base):
    """
    When scraper puts row with `should_process = True` in this table, it becomes eligible for processing.
    Processing is an action of taking `o_filepath` and running processor on it.
    Runs with `should_process = False` represent scraper runs that resulted in the same file as the
    previus run for a target, scraper runs that performed actions with custom scripts etc.
    """

    __tablename__ = "scr_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_targets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ScrapeStatus] = mapped_column(
        Enum(ScrapeStatus, name="scrape_status"),
        nullable=False,
        default=ScrapeStatus.pending,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # False = scrape produced no diff vs previous run, processor should skip it.
    # decided at scrape-finish so the processor never diffs at pop time.
    should_process: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True),
                                              nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    o_filepath: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@final
class ScrProcessedTable(Base):
    __tablename__ = "scr_processed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_runs.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_targets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ProcessStatus] = mapped_column(
        Enum(ProcessStatus, name="process_status"),
        nullable=False,
        default=ProcessStatus.pending,
    )
    o_filepath: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@final
class ApiUserTable(Base):
    __tablename__ = "scr_api_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class RouteType(enum.Enum):
    bus = "bus"
    tram = "tram"
    rail = "rail"
    subway = "subway"
    ferry = "ferry"
    cable_car = "cable_car"
    gondola = "gondola"
    funicular = "funicular"


class ExceptionType(enum.Enum):
    added = "added"
    removed = "removed"


class AddressProvider(enum.Enum):
    osm = "osm"
    google = "google"
    here = "here"
    mapbox = "mapbox"


class UserRole(enum.Enum):
    sys_superuser = "sys_superuser"
    sys_admin = "sys_admin"
    sys_moderator = "sys_moderator"
    sub_default = "sub_default"
    sub_premium = "sub_premium"


def _point() -> Geography:
    return Geography("POINT", srid=4326, spatial_index=False)


@final
class CarriersTable(Base):
    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    homepage: Mapped[str | None] = mapped_column(String)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)


@final
class StopsTable(Base):
    __tablename__ = "stops"
    __table_args__ = (
        Index("stops_spatial_idx", "coordinates", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    coordinates: Mapped[WKBElement | None] = mapped_column(_point())


@final
class RoutesTable(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    carrier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "carriers.id", ondelete="CASCADE", name="routes_carrier_id_carriers_id_fk"
        ),
        nullable=False,
    )
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    long_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String)
    route_type: Mapped[RouteType] = mapped_column(
        Enum(RouteType, name="route_type"), nullable=False
    )
    color: Mapped[str | None] = mapped_column(String(6))
    text_color: Mapped[str | None] = mapped_column(String(6))
    origin_stop: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "stops.id", ondelete="RESTRICT", name="routes_origin_stop_stops_id_fk"
        ),
        nullable=False,
    )
    destination_stop: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "stops.id", ondelete="RESTRICT", name="routes_destination_stop_stops_id_fk"
        ),
        nullable=False,
    )


@final
class CalendarTable(Base):
    __tablename__ = "calendar"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    wednesday: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    thursday: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    saturday: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


# calendar_dates has a column named `date`, which shadows the type inside its class body
DateType: TypeAlias = date


@final
class CalendarDatesTable(Base):
    __tablename__ = "calendar_dates"
    __table_args__ = (
        UniqueConstraint(
            "calendar_id", "date", name="calendar_dates_calendar_id_date_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    calendar_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "calendar.id",
            ondelete="CASCADE",
            name="calendar_dates_calendar_id_calendar_id_fk",
        ),
        nullable=False,
    )
    date: Mapped[DateType] = mapped_column(Date, nullable=False)
    exception_type: Mapped[ExceptionType] = mapped_column(
        Enum(ExceptionType, name="exception_type"), nullable=False
    )


@final
class TripsTable(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("routes.id", ondelete="CASCADE", name="trips_route_id_routes_id_fk"),
        nullable=False,
    )
    calendar_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "calendar.id", ondelete="RESTRICT", name="trips_calendar_id_calendar_id_fk"
        ),
        nullable=False,
    )
    duration: Mapped[int | None] = mapped_column(Integer)
    distance: Mapped[int | None] = mapped_column(Integer)


@final
class FareAttributesTable(Base):
    __tablename__ = "fare_attributes"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    route_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "routes.id", ondelete="CASCADE", name="fare_attributes_route_id_routes_id_fk"
        ),
        nullable=False,
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


@final
class TripStopsTable(Base):
    __tablename__ = "trip_stops"
    __table_args__ = (
        UniqueConstraint(
            "trip_id", "stop_order", name="trip_stops_trip_id_stop_order_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE", name="trip_stops_trip_id_trips_id_fk"),
        nullable=False,
    )
    stop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stops.id", ondelete="RESTRICT", name="trip_stops_stop_id_stops_id_fk"),
        nullable=False,
    )
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)


@final
class StopsMetricsTable(Base):
    __tablename__ = "stops_metrics"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    stop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stops.id", ondelete="CASCADE", name="stops_metrics_stop_id_stops_id_fk"),
        nullable=False,
    )
    click_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


@final
class AddressesTable(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        Index("addresses_spatial_idx", "coordinates", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    street: Mapped[str | None] = mapped_column(String(255))
    house_number: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    postcode: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(2))
    coordinates: Mapped[WKBElement | None] = mapped_column(_point())


@final
class AddressesRawTable(Base):
    __tablename__ = "addresses_raw"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_id", name="addresses_raw_provider_external_id_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    address_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "addresses.id",
            ondelete="CASCADE",
            name="addresses_raw_address_id_addresses_id_fk",
        ),
        nullable=False,
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provider: Mapped[AddressProvider] = mapped_column(
        Enum(AddressProvider, name="address_provider"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255))


@final
class AddressesMetricsTable(Base):
    __tablename__ = "addresses_metrics"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    address_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "addresses.id",
            ondelete="CASCADE",
            name="addresses_metrics_address_id_addresses_id_fk",
        ),
        nullable=False,
    )
    click_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


@final
class WebUsersTable(Base):
    __tablename__ = "web_users"
    __table_args__ = (
        UniqueConstraint("username", name="web_users_username_unique"),
        UniqueConstraint("email", name="web_users_email_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    username: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"))
    last_logged_in: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True))
    premium_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True))
