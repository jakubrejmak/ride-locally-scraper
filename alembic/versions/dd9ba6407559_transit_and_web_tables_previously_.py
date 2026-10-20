"""transit and web tables previously created by drizzle

Revision ID: dd9ba6407559
Revises: 2ff10f1daaee
Create Date: 2026-10-20 18:20:06.950446

Mirrors web/drizzle/0000_lush_kree.sql exactly (names, constraints, indexes).
Databases that already ran that drizzle migration must not apply this one:
    alembic upgrade 2ff10f1daaee
    alembic stamp dd9ba6407559
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dd9ba6407559'
down_revision: Union[str, Sequence[str], None] = '2ff10f1daaee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUMS = {
    "address_provider": ("osm", "google", "here", "mapbox"),
    "exception_type": ("added", "removed"),
    "route_type": ("bus", "tram", "rail", "subway", "ferry", "cable_car", "gondola", "funicular"),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True)


def _point() -> Geometry:
    # no SRID: drizzle generated geometry(point) despite schema.ts asking for 4326
    return Geometry("POINT", spatial_index=False)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind)

    op.create_table(
        "carriers",
        _id(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("homepage", sa.String(), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
    )
    op.create_table(
        "stops",
        _id(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("coordinates", _point(), nullable=True),
    )
    op.create_index("stops_spatial_idx", "stops", ["coordinates"], postgresql_using="gist")
    op.create_table(
        "calendar",
        _id(),
        *[
            sa.Column(day, sa.Boolean(), server_default=sa.false(), nullable=False)
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        ],
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
    )
    op.create_table(
        "addresses",
        _id(),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("house_number", sa.String(length=20), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("postcode", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("coordinates", _point(), nullable=True),
    )
    op.create_index("addresses_spatial_idx", "addresses", ["coordinates"], postgresql_using="gist")
    op.create_table(
        "routes",
        _id(),
        sa.Column("carrier_id", sa.Integer(), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=False),
        sa.Column("long_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("route_type", _enum("route_type"), nullable=False),
        sa.Column("color", sa.String(length=6), nullable=True),
        sa.Column("text_color", sa.String(length=6), nullable=True),
        sa.Column("origin_stop", sa.Integer(), nullable=False),
        sa.Column("destination_stop", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["carrier_id"], ["carriers.id"], name="routes_carrier_id_carriers_id_fk", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_stop"], ["stops.id"], name="routes_origin_stop_stops_id_fk", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_stop"], ["stops.id"], name="routes_destination_stop_stops_id_fk", ondelete="RESTRICT"),
    )
    op.create_table(
        "calendar_dates",
        _id(),
        sa.Column("calendar_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("exception_type", _enum("exception_type"), nullable=False),
        sa.ForeignKeyConstraint(["calendar_id"], ["calendar.id"], name="calendar_dates_calendar_id_calendar_id_fk", ondelete="CASCADE"),
        sa.UniqueConstraint("calendar_id", "date", name="calendar_dates_calendar_id_date_unique"),
    )
    op.create_table(
        "trips",
        _id(),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("calendar_id", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("distance", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name="trips_route_id_routes_id_fk", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calendar_id"], ["calendar.id"], name="trips_calendar_id_calendar_id_fk", ondelete="RESTRICT"),
    )
    op.create_table(
        "fare_attributes",
        _id(),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name="fare_attributes_route_id_routes_id_fk", ondelete="CASCADE"),
    )
    op.create_table(
        "trip_stops",
        _id(),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("stop_id", sa.Integer(), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("arrival_time", sa.Time(), nullable=False),
        sa.Column("departure_time", sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="trip_stops_trip_id_trips_id_fk", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stop_id"], ["stops.id"], name="trip_stops_stop_id_stops_id_fk", ondelete="RESTRICT"),
        sa.UniqueConstraint("trip_id", "stop_order", name="trip_stops_trip_id_stop_order_unique"),
    )
    op.create_table(
        "stops_metrics",
        _id(),
        sa.Column("stop_id", sa.Integer(), nullable=False),
        sa.Column("click_time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stop_id"], ["stops.id"], name="stops_metrics_stop_id_stops_id_fk", ondelete="CASCADE"),
    )
    op.create_table(
        "addresses_raw",
        _id(),
        sa.Column("address_id", sa.Integer(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", _enum("address_provider"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"], name="addresses_raw_address_id_addresses_id_fk", ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "external_id", name="addresses_raw_provider_external_id_unique"),
    )
    op.create_table(
        "addresses_metrics",
        _id(),
        sa.Column("address_id", sa.Integer(), nullable=False),
        sa.Column("click_time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"], name="addresses_metrics_address_id_addresses_id_fk", ondelete="CASCADE"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    for table in (
        "addresses_metrics",
        "addresses_raw",
        "stops_metrics",
        "trip_stops",
        "fare_attributes",
        "trips",
        "calendar_dates",
        "routes",
        "addresses",
        "calendar",
        "stops",
        "carriers",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for name in ENUMS:
        postgresql.ENUM(name=name).drop(bind)
