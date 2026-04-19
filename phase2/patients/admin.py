from django.contrib import admin
from .models import (
    ScreeningTestResult, 
    OnlineSessionRequest, 
    RedeemableService, 
    RedemptionTicket, 
    HomeTestRequest, 
    PatientQuery
)

@admin.register(ScreeningTestResult)
class ScreeningTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_type', 'score', 'created_at')
    list_filter = ('test_type', 'created_at')
    search_fields = ('user__name', 'result_data')

@admin.register(OnlineSessionRequest)
class OnlineSessionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'doctor', 'status', 'scheduled_time', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__name', 'doctor__name')

@admin.register(RedeemableService)
class RedeemableServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'coins_required', 'icon', 'created_at')
    search_fields = ('name',)

@admin.register(RedemptionTicket)
class RedemptionTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'user', 'service', 'redeemed_at', 'is_used')
    list_filter = ('is_used', 'redeemed_at', 'service')
    search_fields = ('ticket_code', 'user__name', 'service__name')
    readonly_fields = ('ticket_code', 'redeemed_at')

@admin.register(HomeTestRequest)
class HomeTestRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'company_name', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'company_name')
    search_fields = ('user__name', 'phone_number', 'company_name', 'address')

@admin.register(PatientQuery)
class PatientQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'phone_number', 'email', 'query_text')
