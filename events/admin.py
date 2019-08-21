from django.contrib import admin
import nested_admin
import json
from .models import Override, Reminder, Recurrence, Event, CalendarEvent, recurrence_dict_2_string
from django.utils.timezone import get_current_timezone
from django.core.serializers.json import DjangoJSONEncoder
from django import forms
from . import google_calendar
from accounts.models import Account
from event_receivers.models import EventReceiver
from .serializers import EventSerializer, ReminderSerializer, OverrideSerializer, RecurrenceSerializer
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser


class OverrideInline(nested_admin.NestedStackedInline):
    model = Override
    extra = 0
    fields = [('method', 'minutes')]


class ReminderInline(nested_admin.NestedStackedInline):
    model = Reminder
    extra = 0
    inlines = [OverrideInline]


class RecurrencInline(nested_admin.NestedStackedInline):
    model = Recurrence
    extra = 0
    radio_fields = {'ends': admin.VERTICAL}
    fields = [
        'rule',
        ('interval', 'freq'),
        ('ends', 'until', 'count')
    ]
    readonly_fields = ['rule']

    
@admin.register(Event)
class EventAdmin(nested_admin.NestedModelAdmin):
    list_display = (
        'id',
        'sender_display',
        'summary',
        'description',
        'start',
        'end',
        'accounts_display',
        'calendar_event_ids_display',
        'created_at',
        'updated_at'
    )
    list_display_links = (
        'id',
        'sender_display',
        'summary',
        'description',
        'start',
        'end',
    )
    list_per_page = 50
    fields = ['sender', 'summary', 'description', ('start', 'end', ), 'accounts', ]
    readonly_fields = ['calendar_event_events']
    filter_horizontal = ('accounts',)
    inlines = [ReminderInline, RecurrencInline]

    def sender_display(self, obj):
        return obj.sender.email

    def accounts_display(self, obj):
        return ", ".join([
            account.email for account in obj.accounts.all()
        ])
    
    def calendar_event_ids_display(self, obj):
        return ", ".join([
            calendar_event.calendar_event_id for calendar_event in obj.calendar_event_events.all()
        ])

    sender_display.short_description = "Sender"
    accounts_display.short_description = "Accounts"
    calendar_event_ids_display.short_description = "Calendar Evnet IDs"

    def save_related(self, request, form, formsets, change):
        obj = form.instance
        calendar_event_ids = []
        # Make event json data
        for account in form.cleaned_data['accounts']:
            event = {
                'summary': obj.summary,
                'location': obj.sender.last_location,
                'description': obj.description,
                'start': {
                    'dateTime': obj.start.isoformat(),
                    'timeZone': get_current_timezone().tzname(None)
                },
                'end': {
                    'dateTime': obj.end.isoformat(), #'2019-08-04T17:00:00-07:00',
                    'timeZone': get_current_timezone().tzname(None) #'America/Los_Angeles',
                },
                'attendees': [{'email': account.email}]
            }
            recurrence_formset_index = 1
            # Check reminder data and add them if set
            if formsets[0] and formsets[0].cleaned_data and formsets[0].cleaned_data[0]:
                # Add useDefault value
                event['reminders'] = ReminderSerializer(formsets[0].cleaned_data[0]).data 
                recurrence_formset_index = 2
                # Add overrides value
                if formsets[1]:
                    event['reminders']['overrides'] = []
                    for override_form in formsets[1]:
                        event['reminders']['overrides'].append(
                            OverrideSerializer(override_form.cleaned_data).data
                        )

            # Check recurrence data and add them if set
            recurrenct_formset = formsets[recurrence_formset_index]
            if recurrenct_formset and recurrenct_formset.cleaned_data:
                # Add recurrence data
                event['recurrence'] = []
                for recurrence_form in recurrenct_formset:
                    str_recurrence = recurrence_dict_2_string(recurrence_form.cleaned_data)
                    if str_recurrence:
                        event['recurrence'].append(str_recurrence)

            # print('====== generate_event: ', event)

            if change:
                # Update event
                google_calendar_event = google_calendar.update_event(
                    obj.calendar_event_id,
                    event, 
                    obj.sender.google_oauth2_client_id,
                    obj.sender.google_oauth2_secrete
                )
            else:
                # Send add_event request to google
                google_calendar_event = google_calendar.add_event(
                    event, 
                    obj.sender.google_oauth2_client_id, 
                    obj.sender.google_oauth2_secrete
                )
                
            if google_calendar_event != None:
                calendar_event_ids.append(google_calendar_event.get('id'))
            
        # Save model
        obj.save()
        super(EventAdmin, self).save_related(request, form, formsets, change)

        # Get the saved event id        
        event_pk = form.instance.id
        if len(calendar_event_ids) > 0: 
            
            # Add EventReceivers for each account matching to this event
            current_event = Event.objects.get(pk=event_pk)

            if change:
                # Remove all associated old event_receivers.
                EventReceiver.objects.filter(event_id=current_event.id).delete()

            # for account in current_event.accounts.all():
            for account in form.cleaned_data['accounts']:
                new_event_receiver = EventReceiver.objects.create(
                    event=current_event,
                    account=account
                )
                new_event_receiver.save()
            
            # Set calndear_event_ids
            if change:
                # Remove all associated old calendar ids
                CalendarEvent.objects.filter(calendar_event_ids=calendar_event_ids).delete()

            for calendar_event_id in calendar_event_ids:
                new_calendar_event = CalendarEvent.objects.create(
                    calendar_event_id=calendar_event_id,
                    event=current_event
                )
                new_calendar_event.save()
            
            # print('===== current_event: ', EventSerializer(current_event).data)


    # def delete_selected(self, request, queryset):
    #     for obj in queryset:
    #         if obj.calendar_event_id:
    #             # Send delete_event request to google
    #             res = google_calendar.delete_event(
    #                 obj.calendar_event_id, 
    #                 obj.sender.google_oauth2_client_id, 
    #                 obj.sender.google_oauth2_secrete
    #             )
    #         obj.delete()