from django.contrib import admin

from .models import Filiere, Module, Semestre


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class FiliereInline(admin.TabularInline):
    model = Filiere
    extra = 0
    show_change_link = True


@admin.register(Semestre)
class SemestreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [FiliereInline]


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ("name", "semestre")
    list_filter = ("semestre",)
    search_fields = ("name",)
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "filiere", "semestre_name")
    list_filter = ("filiere__semestre", "filiere")
    search_fields = ("name",)

    @admin.display(description="Semestre")
    def semestre_name(self, obj):
        return obj.filiere.semestre.name
