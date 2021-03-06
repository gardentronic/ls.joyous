# ------------------------------------------------------------------------------
# Test ical Format
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from django.utils import timezone
from django.test import TestCase, RequestFactory
from wagtail.core.models import Site, Page
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, YEARLY, MO, TU, WE, TH, FR, SA
from ls.joyous.models import (CalendarPage, SimpleEventPage, RecurringEventPage,
        CancellationPage, PostponementPage, ExtraInfoPage, GroupPage)
from ls.joyous.formats.ical import (CalendarTypeError,
        CalendarNotInitializedError, VCalendar)
from freezegun import freeze_time
from .testutils import datetimetz, freeze_timetz, getPage

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = getPage("/home/")
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    @freeze_timetz("2018-05-12 13:00")
    def testFromSimpleCalendarPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "bbq",
                               title = "BBQ",
                               date  = dt.date(2008,7,15),
                               time_from = dt.time(17,30),
                               time_to   = dt.time(19),
                               tz = pytz.timezone("Pacific/Auckland"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vcal = VCalendar.fromPage(self.calendar, self._getRequest("/events/"))
        export = vcal.to_ical()
        props = [b"SUMMARY:BBQ",
                 b"DTSTART;TZID=Pacific/Auckland:20080715T173000",
                 b"DTEND;TZID=Pacific/Auckland:20080715T190000",
                 b"DTSTAMP:20180512T040000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"CREATED:20180512T040000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20180512T040000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/bbq/",]
        for prop in props:
            with self.subTest(prop=prop.split(b'\r\n',1)[0]):
                self.assertIn(prop, export)

    @freeze_timetz("2019-01-21 15:00")
    def testFromCalendarPage(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "chess",
                                  title = "Chess",
                                  repeat = Recurrence(dtstart=dt.date(2000,1,1),
                                                      freq=WEEKLY,
                                                      byweekday=[MO,WE,FR]),
                                  time_from = dt.time(12),
                                  time_to   = dt.time(13))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        cancellation = CancellationPage(owner = self.user,
                                        slug  = "2019-02-04-cancellation",
                                        title = "Cancellation for Monday 4th of February",
                                        overrides = page,
                                        except_date = dt.date(2019, 2, 4),
                                        cancellation_title   = "No Chess Club Today")
        page.add_child(instance=cancellation)
        cancellation.save_revision().publish()
        postponement = PostponementPage(owner = self.user,
                                        slug  = "2019-10-02-postponement",
                                        title = "Postponement for Wednesday 2nd of October",
                                        overrides = page,
                                        except_date = dt.date(2019, 10, 2),
                                        cancellation_title   = "",
                                        postponement_title   = "Early Morning Matches",
                                        date      = dt.date(2019,10,3),
                                        time_from = dt.time(7,30),
                                        time_to   = dt.time(8,30))
        page.add_child(instance=postponement)
        postponement.save_revision().publish()
        vcal = VCalendar.fromPage(self.calendar, self._getRequest("/events/"))
        export = vcal.to_ical()
        props = [b"SUMMARY:Chess",
                 b"DTSTART;TZID=Asia/Tokyo:20000103T120000",
                 b"DTEND;TZID=Asia/Tokyo:20000103T130000",
                 b"DTSTAMP:20190121T060000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;WKST=SU",
                 b"EXDATE;TZID=Asia/Tokyo:20190204T120000",
                 b"CREATED:20190121T060000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20190121T060000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/chess/",
                 b"SUMMARY:Early Morning Matches",
                 b"DTSTART;TZID=Asia/Tokyo:20191003T073000",
                 b"DTEND;TZID=Asia/Tokyo:20191003T083000",
                 b"RECURRENCE-ID;TZID=Asia/Tokyo:20191002T120000", ]
        for prop in props:
            with self.subTest(prop=prop):
                self.assertIn(prop, export)

    @freeze_timetz("2018-05-12 13:00")
    def testFromSimpleEventPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "pet-show",
                               title = "Pet Show",
                               date  = dt.date(1987,6,5),
                               time_from = dt.time(11),
                               time_to   = dt.time(17,30),
                               tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vcal = VCalendar.fromPage(page, self._getRequest("/events/pet-show/"))
        export = vcal.to_ical()
        aest = b"\r\n".join([
                 b"BEGIN:STANDARD",
                 b"DTSTART;VALUE=DATE-TIME:19870315T020000",
                 b"TZNAME:AEST",
                 b"TZOFFSETFROM:+1100",
                 b"TZOFFSETTO:+1000",
                 b"END:STANDARD", ])
        aedt  = b"\r\n".join([
                 b"BEGIN:DAYLIGHT",
                 b"DTSTART;VALUE=DATE-TIME:19871025T030000",
                 b"TZNAME:AEDT",
                 b"TZOFFSETFROM:+1000",
                 b"TZOFFSETTO:+1100",
                 b"END:DAYLIGHT", ])
        props = [b"SUMMARY:Pet Show",
                 b"DTSTART;TZID=Australia/Sydney:19870605T110000",
                 b"DTEND;TZID=Australia/Sydney:19870605T173000",
                 b"DTSTAMP:20180512T040000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"CREATED:20180512T040000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20180512T040000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/pet-show/",
                 aest,
                 aedt]
        for prop in props:
            with self.subTest(prop=prop.split(b'\r\n',1)[0]):
                self.assertIn(prop, export)

    @freeze_timetz("2019-01-21 13:00")
    def testFromEventPage(self):
        chess = GroupPage(slug="chess-club", title="Chess Club")
        self.home.add_child(instance=chess)
        page = RecurringEventPage(owner = self.user,
                                  slug  = "chess",
                                  title = "Chess",
                                  repeat = Recurrence(dtstart=dt.date(2000,1,1),
                                                      freq=WEEKLY,
                                                      byweekday=[MO,WE,FR]),
                                  time_from = dt.time(12),
                                  time_to   = dt.time(13))
        chess.add_child(instance=page)
        page.save_revision().publish()
        postponement = PostponementPage(owner = self.user,
                                        slug  = "2019-10-02-postponement",
                                        title = "Postponement for Wednesday 2nd of October",
                                        overrides = page,
                                        except_date = dt.date(2019, 10, 2),
                                        cancellation_title   = "",
                                        postponement_title   = "Early Morning Matches",
                                        date      = dt.date(2019,10,3),
                                        time_from = dt.time(7,30),
                                        time_to   = dt.time(8,30))
        page.add_child(instance=postponement)
        postponement.save_revision().publish()
        vcal = VCalendar.fromPage(page, self._getRequest("/events/chess/"))
        export = vcal.to_ical()
        props = [b"SUMMARY:Chess",
                 b"DTSTART;TZID=Asia/Tokyo:20000103T120000",
                 b"DTEND;TZID=Asia/Tokyo:20000103T130000",
                 b"DTSTAMP:20190121T040000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;WKST=SU",
                 b"CREATED:20190121T040000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20190121T040000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/chess-club/chess/",
                 b"SUMMARY:Early Morning Matches",
                 b"DTSTART;TZID=Asia/Tokyo:20191003T073000",
                 b"DTEND;TZID=Asia/Tokyo:20191003T083000",
                 b"RECURRENCE-ID;TZID=Asia/Tokyo:20191002T120000", ]
        for prop in props:
            with self.subTest(prop=prop):
                self.assertIn(prop, export)

    def testFromUnsupported(self):
        page = Page(owner = self.user,
                    slug  = "thoughts",
                    title = "My thoughts for today")
        self.home.add_child(instance=page)
        page.save_revision().publish()
        with self.assertRaises(CalendarTypeError):
            VCalendar.fromPage(page, self._getRequest("/thoughts/"))

    def testEmptyCalendar(self):
        vcal = VCalendar(self.calendar)
        idParts = vcal['PRODID'].split("//")
        self.assertEqual(len(idParts), 4)
        self.assertEqual(idParts[0], "-")
        self.assertEqual(idParts[1], "linuxsoftware.nz")
        self.assertEqual(idParts[2][:14], "NONSGML Joyous")
        self.assertEqual(idParts[3], "EN")
        self.assertEqual(vcal['VERSION'], "2.0")

    def testLoad(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"BEGIN:VEVENT",
                b"DTSTART;TZID=UTC+0:20180407T093000",
                b"DTEND;TZID=UTC+0:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"UID:978-1523093400-1523100600@bloorneighbours.ca",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        vcal.load(self._getRequest(), data)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.owner,      self.user)
        self.assertEqual(event.slug,       "mini-fair-garage-sale")
        self.assertEqual(event.title,      "Mini-Fair & Garage Sale")
        self.assertEqual(event.details,    "")
        self.assertEqual(event.date,       dt.date(2018,4,7))
        self.assertEqual(event.time_from,  dt.time(9,30))
        self.assertEqual(event.time_to,    dt.time(11,30))

    def testLoadInvalidFile(self):
        data  = b"FOO:BAR:SNAFU"
        vcal = VCalendar(self.calendar)
        request = self._getRequest()
        vcal.load(request, data)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg.level, messages.ERROR)
        self.assertEqual(msg.message, "Could not parse iCalendar file ")

    def testLoadEventMissingUID(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"BEGIN:VEVENT",
                b"DTSTART;TZID=UTC+0:20180407T093000",
                b"DTEND;TZID=UTC+0:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        request = self._getRequest()
        vcal.load(request, data)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 0)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg.level, messages.ERROR)
        self.assertEqual(msg.message, "Could not load 1 iCal events")

    def testLoadUnknownTZ(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"X-WR-TIMEZONE:Canada/Toronto",
                b"BEGIN:VEVENT",
                b"UID:978-1523093400-1523100600@bloorneighbours.ca",
                b"DTSTART:20180407T093000",
                b"DTEND:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        request = self._getRequest()
        vcal.load(request, data)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].tz.zone, "Asia/Tokyo")
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].level, messages.WARNING)
        self.assertEqual(msgs[0].message, "Unknown time zone Canada/Toronto")
        self.assertEqual(msgs[1].level, messages.SUCCESS)
        self.assertEqual(msgs[1].message, "1 iCal events loaded")

# ------------------------------------------------------------------------------
class TestUpdate(TestCase):
    @freeze_timetz("2018-02-01 13:00")
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = getPage("/home/")
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug   = "mini-fair",
                                title  = "Mini-Fair",
                                date   = dt.date(2018,4,7),
                                uid = "978-1523093400-1523100600@bloorneighbours.ca")
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "tango-thursdays",
                                   title = "Tango Thursdays",
                                   details = "Weekly tango lessons at the Dance Spot",
                                   repeat  = Recurrence(dtstart=dt.date(2018,3,29),
                                                        freq=WEEKLY,
                                                        byweekday=[TH]),
                                   time_from = dt.time(19,30),
                                   time_to   = dt.time(22,0),
                                   tz        = pytz.timezone("US/Eastern"),
                                   website   = "http://torontodancespot.com/",
                                   location  = "622 Bloor St. W., Toronto ON, M6G 1K7",
                                   uid = "645-1524080440-854495893@bloorneighbours.ca")
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        cancellation = CancellationPage(owner = self.user,
                                        slug  = "2019-02-14-cancellation",
                                        title = "Cancellation for Thursday 14th of April",
                                        overrides = event,
                                        except_date = dt.date(2019, 2, 14))
        event.add_child(instance=cancellation)
        cancellation.save_revision().publish()
        info = ExtraInfoPage(owner = self.user,
                             slug  = "2018-04-05-extra-info",
                             title = "Extra-Info for Thursday 5th of April",
                             overrides = event,
                             except_date = dt.date(2018, 4, 5),
                             extra_title = "Performance",
                             extra_information = "Performance for the public")
        event.add_child(instance=info)
        info.save_revision().publish()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    @freeze_timetz("2018-03-06 9:00")
    def testLoadSimple(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"BEGIN:VEVENT",
                b"DTSTART;TZID=UTC+0:20180407T093000",
                b"DTEND;TZID=UTC+0:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"UID:978-1523093400-1523100600@bloorneighbours.ca",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        vcal.load(self._getRequest(), data)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.owner,      self.user)
        self.assertEqual(event.slug,       "mini-fair")
        self.assertEqual(event.title,      "Mini-Fair & Garage Sale")
        self.assertEqual(event.date,       dt.date(2018,4,7))
        self.assertEqual(event.time_from,  dt.time(9,30))
        self.assertEqual(event.time_to,    dt.time(11,30))
        revisions = event.revisions.all()
        self.assertEqual(len(revisions), 2)
        rev1, rev2 = revisions
        self.assertEqual(rev1.created_at, datetimetz(2018, 2, 1, 13, 0))
        self.assertEqual(rev2.created_at, datetimetz(2018, 3, 6, 9, 0))

    @freeze_timetz("2018-04-08 10:00")
    @timezone.override("America/Toronto")
    def testLoadRecurring(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"BEGIN:VEVENT",
                b"SUMMARY:Fierce Tango",
                b"DESCRIPTION:Argentine Show Tango Performance",
                b"DTSTART:20180405T193000",
                b"DTEND:20180405T220000",
                b"RECURRENCE-ID:20180405T193000",
                b"DTSTAMP:20180408T094745Z",
                b"LAST-MODIFIED:20180314T010000Z",
                b"UID:645-1524080440-854495893@bloorneighbours.ca",
                b"END:VEVENT",
                b"BEGIN:VEVENT",
                b"SUMMARY:Tango Thursdays",
                b"DESCRIPTION:Weekly tango lessons at the Dance Spot",
                b"DTSTART:20180329T193000",
                b"DTEND:20180329T220000",
                b"RRULE:FREQ=WEEKLY;BYDAY=TH",
                b"DTSTAMP:20180408T094745Z",
                b"LAST-MODIFIED:20180131T010000Z",
                b"EXDATE:20181025T193000",
                b"LOCATION:622 Bloor St. W., Toronto ON, M6G 1K7",
                b"SUMMARY:Tango Thursdays",
                b"UID:645-1524080440-854495893@bloorneighbours.ca",
                b"URL:http://torontodancespot.com/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        vcal.load(self._getRequest(), data)
        events = RecurringEventPage.events.child_of(self.calendar).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.slug,  "tango-thursdays")
        self.assertEqual(event.title, "Tango Thursdays")
        self.assertEqual(repr(event.repeat),
                        "DTSTART:20180329\n" \
                        "RRULE:FREQ=WEEKLY;WKST=SU;BYDAY=TH")
        self.assertEqual(event.time_from,  dt.time(19,30))
        self.assertEqual(event.time_to,    dt.time(22,0))
        revisions = event.revisions.all()
        self.assertEqual(len(revisions), 1)
        info = ExtraInfoPage.events.child_of(event).get()
        self.assertEqual(info.slug,  "2018-04-05-extra-info")
        self.assertEqual(info.title, "Extra-Info for Thursday 5th of April")
        self.assertEqual(info.extra_title, "Fierce Tango")
        self.assertEqual(info.extra_information, "Argentine Show Tango Performance")
        self.assertEqual(info.except_date, dt.date(2018,4,5))
        revisions = info.revisions.all()
        self.assertEqual(len(revisions), 2)
        cancellations = CancellationPage.events.child_of(event).all()
        self.assertEqual(len(cancellations), 2)
        cancellation = cancellations[0]
        self.assertEqual(cancellation.except_date, dt.date(2019,2,14))
        cancellation = cancellations[1]
        self.assertEqual(cancellation.except_date, dt.date(2018,10,25))

# ------------------------------------------------------------------------------
class TestNoCalendar(TestCase):
    @freeze_timetz("2012-08-01 13:00")
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        home = getPage("/home/")
        chess = GroupPage(slug="chess-club", title="Chess Club")
        home.add_child(instance=chess)
        chess.save_revision().publish()
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "chess",
                                        title = "Chess Matches",
                                        repeat = Recurrence(dtstart=dt.date(2012,8,1),
                                                            freq=WEEKLY,
                                                            byweekday=[MO,WE,FR]),
                                        time_from = dt.time(12),
                                        time_to   = dt.time(13))
        chess.add_child(instance=self.event)
        self.event.save_revision().publish()
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.request.site = Site.objects.get(is_default_site=True)

    @freeze_timetz("2019-12-01 9:00")
    def testFromEventPage(self):
        vcal = VCalendar.fromPage(self.event, self.request)
        export = vcal.to_ical()
        props = [b"SUMMARY:Chess Matches",
                 b"DTSTART;TZID=Asia/Tokyo:20120801T120000",
                 b"DTEND;TZID=Asia/Tokyo:20120801T130000",
                 b"DTSTAMP:20191201T000000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;WKST=SU",
                 b"CREATED:20120801T040000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20120801T040000Z",
                 b"LOCATION:",
                 b"URL:http://localhost/chess-club/chess/", ]
        for prop in props:
            with self.subTest(prop=prop):
                self.assertIn(prop, export)

    def testNotInitializedLoad(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"BEGIN:VEVENT",
                b"DTSTART;TZID=UTC+0:20180407T093000",
                b"DTEND;TZID=UTC+0:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"UID:978-1523093400-1523100600@bloorneighbours.ca",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar()
        with self.assertRaises(CalendarNotInitializedError):
            vcal.load(self.request, data)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
