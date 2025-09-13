#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D-Print CostCulator
A Python program with GUI for calculating the real costs of 3D printing

xscr33mLabs © 2025
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors

# Optional PIL import for icon support
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import LanguageManager
from language_manager import language_manager


@dataclass
class FilamentType:
    """Data class for a filament type"""
    name: str
    cost_per_kg: float
    
    def __str__(self):
        return f"{self.name} ({self.cost_per_kg:.2f} €/kg)"


@dataclass
class PrinterType:
    """Data class for a printer type"""
    name: str
    power: float  # Watts
    
    def __str__(self):
        return f"{self.name} ({self.power:.0f}W)"


@dataclass
class DryerType:
    """Data class for a dryer type"""
    name: str
    power: float  # Watts
    
    def __str__(self):
        return f"{self.name} ({self.power:.0f}W)"


@dataclass
class PrintProject:
    """Data class for a 3D printing project"""
    project_name: str = ""
    model_name: str = ""
    model_count: int = 1
    print_duration: float = 0.0  # Hours
    
    # Filament
    filament_name: str = ""
    filament_amount: float = 0.0  # Grams
    filament_cost_per_kg: float = 0.0  # Euro per kg
    
    # Printer
    printer_name: str = ""  # Newly added
    printer_power: float = 0.0  # Watts
    electricity_cost: float = 0.0  # Euro per kWh
    
    # Optional filament dryer
    dryer_enabled: bool = False
    dryer_name: str = ""
    dryer_power: float = 0.0  # Watts
    
    # Wear costs
    wear_cost_percent: float = 0.0  # Percent
    
    # Calculated values
    filament_cost: float = 0.0
    electricity_cost_printer: float = 0.0
    electricity_cost_dryer: float = 0.0
    wear_cost: float = 0.0
    # Detailed wear cost breakdown
    mechanical_wear_cost: float = 0.0
    time_wear_cost: float = 0.0
    electronic_wear_cost: float = 0.0
    total_cost: float = 0.0
    
    created_date: str = ""
    modified_date: str = ""


class CostCulator:
    """Class for cost calculations"""
    
    @staticmethod
    def calculate_filament_cost(amount_g: float, cost_per_kg: float, model_count: int) -> float:
        """Calculates filament cost - amount_g is already the total amount for all models"""
        if amount_g <= 0 or cost_per_kg <= 0:
            return 0.0
        return (amount_g / 1000) * cost_per_kg
    
    @staticmethod
    def calculate_electricity_cost(power_watts: float, duration_hours: float, cost_per_kwh: float) -> float:
        """Calculates electricity costs for a device"""
        if power_watts <= 0 or duration_hours <= 0 or cost_per_kwh <= 0:
            return 0.0
        return (power_watts / 1000) * duration_hours * cost_per_kwh
    
    @staticmethod
    def calculate_wear_cost(base_cost: float, wear_percent: float) -> float:
        """Calculates wear costs (deprecated - replaced by automatic calculation)"""
        if base_cost <= 0 or wear_percent < 0:
            return 0.0
        return base_cost * (wear_percent / 100)
    
    @staticmethod
    def calculate_automatic_wear_cost(filament_amount: float, print_duration: float, 
                                     filament_cost: float, electricity_cost: float) -> tuple:
        """Automatically calculates wear costs based on filament consumption and print time
        
        Calculation is based on realistic wear factors:
        - Mechanical wear: 0.01% of material costs per gram of filament
        - Time-based wear: 0.05 Euro per hour of print time
        - Electronic wear: 0.5% of electricity costs
        
        Returns:
            tuple: (total_wear_cost, mechanical_wear, time_wear, electronic_wear)
        """
        mechanical_wear = 0.0
        time_wear = 0.0
        electronic_wear = 0.0
        
        # Mechanical wear based on filament consumption (hotend, extruder, etc.)
        if filament_amount > 0:
            # 0.01% of filament costs per gram as wear
            mechanical_wear = filament_cost * 0.0001 * filament_amount
        
        # Time-based wear (motors, fans, bearings, etc.)
        if print_duration > 0:
            # 0.05 Euro per hour of print time as flat rate for time-based wear
            time_wear = print_duration * 0.05
        
        # Electronic wear based on power consumption
        if electricity_cost > 0:
            # 0.5% of electricity costs as electronic wear
            electronic_wear = electricity_cost * 0.005
        
        total_wear_cost = mechanical_wear + time_wear + electronic_wear
        return total_wear_cost, mechanical_wear, time_wear, electronic_wear
    
    @classmethod
    def calculate_total_costs(cls, project: PrintProject) -> PrintProject:
        """Calculates all costs for a project"""
        # Filament costs
        project.filament_cost = cls.calculate_filament_cost(
            project.filament_amount,
            project.filament_cost_per_kg,
            project.model_count
        )
        
        # Printer electricity costs
        project.electricity_cost_printer = cls.calculate_electricity_cost(
            project.printer_power,
            project.print_duration,
            project.electricity_cost
        )
        
        # Dryer electricity costs (optional)
        if project.dryer_enabled:
            project.electricity_cost_dryer = cls.calculate_electricity_cost(
                project.dryer_power,
                project.print_duration,
                project.electricity_cost
            )
        else:
            project.electricity_cost_dryer = 0.0
        
        # Base costs (Material + electricity)
        base_cost = project.filament_cost + project.electricity_cost_printer + project.electricity_cost_dryer
        
        # Automatic wear costs based on filament consumption and print time
        wear_result = cls.calculate_automatic_wear_cost(
            project.filament_amount,
            project.print_duration,
            project.filament_cost,
            project.electricity_cost_printer + project.electricity_cost_dryer
        )
        
        project.wear_cost, project.mechanical_wear_cost, project.time_wear_cost, project.electronic_wear_cost = wear_result
        
        # Total costs
        project.total_cost = base_cost + project.wear_cost
        
        return project


class FilamentManager:
    """Class for managing filament types"""
    
    def __init__(self):
        self.filaments_file = "filaments.json"
        self.filaments = self.load_filaments()
    
    def load_filaments(self) -> list[FilamentType]:
        """Loads the filament list from the JSON file"""
        try:
            if os.path.exists(self.filaments_file):
                with open(self.filaments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [FilamentType(**item) for item in data]
        except Exception as e:
            print(f"Error loading filaments: {e}")
        
    # Default filaments if file doesn't exist
        return [
            FilamentType("eSun PLA+ Black", 16.99),
        ]
    
    def save_filaments(self) -> bool:
        """Saves the filament list to the JSON file"""
        try:
            data = [asdict(filament) for filament in self.filaments]
            with open(self.filaments_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving filaments: {e}")
            return False
    
    def add_filament(self, name: str, cost_per_kg: float) -> bool:
        """Adds a new filament"""
        # Check if filament already exists
        for filament in self.filaments:
            if filament.name.lower() == name.lower():
                return False  # Already exists
        
        self.filaments.append(FilamentType(name, cost_per_kg))
        return self.save_filaments()
    
    def get_filament_by_name(self, name: str) -> Optional[FilamentType]:
        """Finds a filament by name"""
        for filament in self.filaments:
            if filament.name == name:
                return filament
        return None
    
    def get_filament_names(self) -> list[str]:
        """Returns a list of all filament names"""
        return [filament.name for filament in self.filaments]
    
    def remove_filament(self, name: str) -> bool:
        """Removes a filament by name"""
        for i, filament in enumerate(self.filaments):
            if filament.name == name:
                self.filaments.pop(i)
                return self.save_filaments()
        return False  # Filament not found


class PrinterManager:
    """Class for managing printer types"""
    
    def __init__(self):
        self.printers_file = "printers.json"
        self.printers = self.load_printers()
    
    def load_printers(self) -> list[PrinterType]:
        """Loads the printer list from the JSON file"""
        try:
            if os.path.exists(self.printers_file):
                with open(self.printers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [PrinterType(**item) for item in data]
        except Exception as e:
            print(f"Error loading printers: {e}")
        
    # Default printers if file doesn't exist
        return [
            PrinterType("Anycubic i3 Mega S", 150.0)
        ]
    
    def save_printers(self) -> bool:
        """Saves the printer list to the JSON file"""
        try:
            data = [asdict(printer) for printer in self.printers]
            with open(self.printers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving printers: {e}")
            return False
    
    def add_printer(self, name: str, power: float) -> bool:
        """Adds a new printer"""
        # Check if printer already exists
        for printer in self.printers:
            if printer.name.lower() == name.lower():
                return False  # Already exists
        
        self.printers.append(PrinterType(name, power))
        return self.save_printers()
    
    def get_printer_by_name(self, name: str) -> Optional[PrinterType]:
        """Finds a printer by name"""
        for printer in self.printers:
            if printer.name == name:
                return printer
        return None
    
    def get_printer_names(self) -> list[str]:
        """Returns a list of all printer names"""
        return [printer.name for printer in self.printers]
    
    def remove_printer(self, name: str) -> bool:
        """Removes a printer by name"""
        for i, printer in enumerate(self.printers):
            if printer.name == name:
                self.printers.pop(i)
                return self.save_printers()
        return False  # Printer not found


class DryerManager:
    """Class for managing dryer types"""
    
    def __init__(self):
        self.dryers_file = "dryers.json"
        self.dryers = self.load_dryers()
    
    def load_dryers(self) -> list[DryerType]:
        """Loads the dryer list from the JSON file"""
        try:
            if os.path.exists(self.dryers_file):
                with open(self.dryers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [DryerType(**item) for item in data]
        except Exception as e:
            print(f"Error loading dryers: {e}")
        
        # Default dryers if file doesn't exist
        return [
            DryerType("SUNLU S2", 48.0),
        ]
    
    def save_dryers(self) -> bool:
        """Saves the dryer list to the JSON file"""
        try:
            data = [asdict(dryer) for dryer in self.dryers]
            with open(self.dryers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving dryers: {e}")
            return False
    
    def add_dryer(self, name: str, power: float) -> bool:
        """Adds a new dryer"""
        # Check if dryer already exists
        for dryer in self.dryers:
            if dryer.name.lower() == name.lower():
                return False  # Already exists
        
        self.dryers.append(DryerType(name, power))
        return self.save_dryers()
    
    def get_dryer_by_name(self, name: str) -> Optional[DryerType]:
        """Finds a dryer by name"""
        for dryer in self.dryers:
            if dryer.name == name:
                return dryer
        return None
    
    def get_dryer_names(self) -> list[str]:
        """Returns a list of all dryer names"""
        return [dryer.name for dryer in self.dryers]
    
    def remove_dryer(self, name: str) -> bool:
        """Removes a dryer by name"""
        for i, dryer in enumerate(self.dryers):
            if dryer.name == name:
                self.dryers.pop(i)
                return self.save_dryers()
        return False  # Dryer not found


class ProjectManager:
    """Class for saving and loading projects"""
    
    @staticmethod
    def save_project(project: PrintProject, filepath: str) -> bool:
        """Saves a project as a JSON file"""
        try:
            project.modified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not project.created_date:
                project.created_date = project.modified_date
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(project), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            from language_manager import language_manager
            messagebox.showerror(language_manager.t("messages.error.title"), 
                               language_manager.t("messages.success.project_save_error", error=str(e)))
            return False
    
    @staticmethod
    def load_project(filepath: str) -> Optional[PrintProject]:
        """Loads a project from a JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return PrintProject(**data)
        except Exception as e:
            from language_manager import language_manager
            messagebox.showerror(language_manager.t("messages.error.title"), 
                               language_manager.t("messages.success.project_load_error", error=str(e)))
            return None


class PDFExporter:
    """Class for PDF export in professional quotation format"""
    
    @staticmethod
    def export_to_pdf(project: PrintProject, filepath: str, language_manager) -> bool:
        """Exports project results as professional quotation PDF"""
        try:
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            from reportlab.lib.styles import ParagraphStyle
            
            doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, 
                                  leftMargin=1*cm, rightMargin=1*cm)
            story = []
            styles = getSampleStyleSheet()
            
            # Define custom styles (more compact)
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=5,
                textColor=colors.HexColor('#2E4057')
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=2,
                textColor=colors.HexColor('#2E4057'),
                borderWidth=1,
                borderColor=colors.HexColor('#2E4057'),
                borderPadding=5
            )
            
            # TITLE
            story.append(Paragraph(language_manager.t("pdf.title"), title_style))
            
            # PROJECT INFORMATION
            story.append(Paragraph(language_manager.t("pdf.project_info"), subtitle_style))
            
            # Determine correct translation for model count
            models_text_key = "pdf.parameters.for_models_singular" if project.model_count == 1 else "pdf.parameters.for_models_plural"
            models_text = language_manager.t(models_text_key, count=project.model_count)
            dryer_info = language_manager.t("pdf.parameters.not_used") if not project.dryer_enabled else f"{language_manager.t('pdf.parameters.power', power=project.dryer_power)}"
            
            project_data = [
                [language_manager.t("pdf.parameters.parameter"), language_manager.t("pdf.parameters.value"), language_manager.t("pdf.parameters.additional_info")],
                [language_manager.t("pdf.parameters.project_name"), project.project_name, ''],
                [language_manager.t("pdf.parameters.model"), project.model_name, ""],
                [language_manager.t("pdf.parameters.print_duration"), f"{project.print_duration:.1f}h {language_manager.t('pdf.parameters.total_for')}", models_text],
                [language_manager.t("pdf.parameters.printer"), project.printer_name, language_manager.t("pdf.parameters.power", power=project.printer_power)],
                [language_manager.t("pdf.parameters.material"), project.filament_name, language_manager.t("pdf.parameters.amount", amount=project.filament_amount, price=project.filament_cost_per_kg)],
                [language_manager.t("pdf.parameters.dryer"), project.dryer_name if project.dryer_enabled else language_manager.t("pdf.parameters.not_used"), dryer_info],
                [language_manager.t("pdf.parameters.electricity_rate"), f"{project.electricity_cost:.4f} €/kWh", ''],
            ]
            
            project_table = Table(project_data, colWidths=[4.5*cm, 6*cm, 6.5*cm])
            project_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4057')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Column spans for project name and model name rows
                ('SPAN', (1, 1), (2, 1)),  # Project name row spans columns 1-2
                ('SPAN', (1, 2), (2, 2)),  # Model name row spans columns 1-2
                
                # Parameter Column
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F8F9FA')),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (0, -1), 9),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                
                # Value and Additional Info Columns
                ('FONTSIZE', (1, 1), (-1, -1), 9),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                
                # General formatting
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(project_table)
            story.append(Spacer(1, 0.3*cm))
            
            # COST BREAKDOWN
            story.append(Paragraph(language_manager.t("pdf.cost_breakdown"), subtitle_style))
            
            cost_data = [
                [language_manager.t("pdf.costs.position"), language_manager.t("pdf.costs.calculation"), language_manager.t("pdf.costs.amount")],
                [language_manager.t("pdf.costs.material_costs"), 
                 f"{project.filament_amount:.0f}g × {project.filament_cost_per_kg:.2f}€/kg", 
                 f"{project.filament_cost:.2f} €"],
                [language_manager.t("pdf.costs.electricity_printer"), 
                 f"{project.printer_power:.0f}W × {project.print_duration:.1f}h × {project.electricity_cost:.4f}€/kWh", 
                 f"{project.electricity_cost_printer:.2f} €"],
            ]
            
            if project.dryer_enabled:
                cost_data.append([language_manager.t("pdf.costs.electricity_dryer"), 
                                f"{project.dryer_power:.0f}W × {project.print_duration:.1f}h × {project.electricity_cost:.4f}€/kWh", 
                                f"{project.electricity_cost_dryer:.2f} €"])
            
            # Detailed wear cost breakdown
            cost_data.append([language_manager.t("pdf.costs.wear_maintenance"), 
                            language_manager.t("pdf.costs.wear_breakdown"), 
                            f"{project.wear_cost:.2f} €"])
            
            cost_data.append([f"  • {language_manager.t('pdf.costs.mechanical_wear')}", 
                            language_manager.t("pdf.costs.mechanical_wear_calc"), 
                            f"{project.mechanical_wear_cost:.2f} €"])
            
            cost_data.append([f"  • {language_manager.t('pdf.costs.time_wear')}", 
                            language_manager.t("pdf.costs.time_wear_calc"), 
                            f"{project.time_wear_cost:.2f} €"])
            
            cost_data.append([f"  • {language_manager.t('pdf.costs.electronic_wear')}", 
                            language_manager.t("pdf.costs.electronic_wear_calc"), 
                            f"{project.electronic_wear_cost:.2f} €"])
            
            cost_table = Table(cost_data, colWidths=[5*cm, 7*cm, 5*cm])
            cost_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4057')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Cost item column
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F8F9FA')),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (0, -1), 9),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                
                # Calculation and amount columns
                ('FONTSIZE', (1, 1), (1, -1), 8),
                ('FONTSIZE', (2, 1), (2, -1), 9),
                ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                
                # General formatting
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(cost_table)
            story.append(Spacer(1, 0.3*cm))
            
            # COST SUMMARY
            story.append(Paragraph(language_manager.t("pdf.cost_summary"), subtitle_style))
            
            total_data = [
                [language_manager.t("pdf.costs.position"), language_manager.t("pdf.costs.amount"), language_manager.t("pdf.costs.percentage_of_total")],
                [language_manager.t("pdf.costs.material_costs"), f"{project.filament_cost:.2f} €", f"{(project.filament_cost/project.total_cost*100):.1f}%"],
                [language_manager.t("pdf.costs.electricity_printer"), f"{project.electricity_cost_printer:.2f} €", f"{(project.electricity_cost_printer/project.total_cost*100):.1f}%"],
            ]
            
            if project.dryer_enabled:
                total_data.append([language_manager.t("pdf.costs.electricity_dryer"), f"{project.electricity_cost_dryer:.2f} €", f"{(project.electricity_cost_dryer/project.total_cost*100):.1f}%"])
            
            # Determine unit text for pieces
            for_x_pieces_text = language_manager.t("units.for_x_pieces", count=project.model_count)
            
            total_data.extend([
                [language_manager.t("pdf.costs.wear_maintenance"), f"{project.wear_cost:.2f} €", f"{(project.wear_cost/project.total_cost*100):.1f}%"],
                [language_manager.t("pdf.costs.total_costs"), f"{project.total_cost:.2f} €", '100.0%'],
                [language_manager.t("pdf.costs.cost_per_model"), f"{(project.total_cost/project.model_count):.2f} €", for_x_pieces_text],
            ])
            
            total_table = Table(total_data, colWidths=[6*cm, 5*cm, 6*cm])
            total_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4057')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Total costs row
                ('BACKGROUND', (0, -2), (-1, -2), colors.HexColor('#4A6FA5')),
                ('TEXTCOLOR', (0, -2), (-1, -2), colors.whitesmoke),
                ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -2), (-1, -2), 11),
                
                # Per model row (gently highlighted)
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FD')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                
                # Separation line above total costs
                ('LINEBELOW', (0, -3), (-1, -3), 2, colors.HexColor('#CCCCCC')),
                
                # Other rows
                ('FONTSIZE', (0, 1), (-1, -4), 9),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -3), 1, colors.HexColor('#DDDDDD')),
                ('GRID', (0, -2), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(total_table)
            story.append(Spacer(1, 1*cm))
            
            # Footer
            footer_text = language_manager.t("pdf.footer", date=datetime.now().strftime("%d.%m.%Y %H:%M"))
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#666666'),
                spaceAfter=0,
                spaceBefore=0
            )
            story.append(Paragraph(footer_text, footer_style))
            
            # Create PDF
            doc.build(story)
            return True
            
        except Exception as e:
            messagebox.showerror(language_manager.t("messages.error.title"), 
                               language_manager.t("messages.success.pdf_creation_error", error=str(e)))
            return False


class FilamentDialog:
    """Dialog for adding new filaments"""
    
    def __init__(self, parent, filament_manager: FilamentManager, language_manager):
        self.parent = parent
        self.filament_manager = filament_manager
        self.language_manager = language_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.language_manager.t("dialogs.filament.title"))
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        self.setup_dialog()
        
    # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_dialog(self):
        """Creates the dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.filament.title"), 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Filament Name
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.filament.name")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        name_entry.focus()
        
        # Cost per kg
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.filament.cost")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.cost_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.cost_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.filament.add_button"), 
                  command=self.add_filament).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.filament.cancel_button"), 
                  command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        
        # Enter-Key Binding
        self.dialog.bind('<Return>', lambda e: self.add_filament())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def add_filament(self):
        """Adds the new filament"""
        name = self.name_var.get().strip()
        cost_str = self.cost_var.get().strip().replace(',', '.')
        
        if not name:
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.name_required"))
            return
        
        try:
            cost = float(cost_str)
            if cost <= 0:
                raise ValueError(self.language_manager.t("messages.error.cost_required"))
        except ValueError as ve:
            messagebox.showerror(self.language_manager.t("messages.error.title"), str(ve))
            return
        
        # Check if already exists
        if not self.filament_manager.add_filament(name, cost):
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.filament_exists", name=name))
            return
        
        # Successfully added
        self.result = FilamentType(name, cost)
        messagebox.showinfo(self.language_manager.t("messages.success.title"), self.language_manager.t("messages.success.filament_added", name=name))
        self.dialog.destroy()
    
    def cancel(self):
        """Cancels the dialog"""
        self.dialog.destroy()


class PrinterDialog:
    """Dialog for adding new printers"""
    
    def __init__(self, parent, printer_manager, language_manager):
        self.parent = parent
        self.printer_manager = printer_manager
        self.language_manager = language_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.language_manager.t("dialogs.printer.title"))
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        self.setup_dialog()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_dialog(self):
        """Creates the dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.printer.title"), 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Printer name
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.printer.name")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        name_entry.focus()
        
        # Power consumption in watts
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.printer.power")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.power_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.power_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.printer.add_button"), 
                  command=self.add_printer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.printer.cancel_button"), 
                  command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        
        # Enter-Key Binding
        self.dialog.bind('<Return>', lambda e: self.add_printer())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def add_printer(self):
        """Adds the new printer"""
        name = self.name_var.get().strip()
        power_str = self.power_var.get().strip().replace(',', '.')
        
        if not name:
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.name_required"))
            return
        
        try:
            power = float(power_str)
            if power <= 0:
                raise ValueError(self.language_manager.t("messages.error.power_required"))
        except ValueError as ve:
            messagebox.showerror(self.language_manager.t("messages.error.title"), str(ve))
            return
        
        # Check if already exists
        if not self.printer_manager.add_printer(name, power):
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.printer_exists", name=name))
            return
        
        # Successfully added
        self.result = PrinterType(name, power)
        messagebox.showinfo(self.language_manager.t("messages.success.title"), self.language_manager.t("messages.success.printer_added", name=name))
        self.dialog.destroy()
    
    def cancel(self):
        """Cancels the dialog"""
        self.dialog.destroy()


class DryerDialog:
    """Dialog for adding new dryers"""
    
    def __init__(self, parent, dryer_manager, language_manager):
        self.parent = parent
        self.dryer_manager = dryer_manager
        self.language_manager = language_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.language_manager.t("dialogs.dryer.title"))
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        self.setup_dialog()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_dialog(self):
        """Creates the dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.dryer.title"), 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Dryer Name
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.dryer.name")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        name_entry.focus()
        
        # Power consumption in watts
        ttk.Label(main_frame, text=self.language_manager.t("dialogs.dryer.power")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.power_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.power_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.dryer.add_button"), 
                  command=self.add_dryer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.language_manager.t("dialogs.dryer.cancel_button"), 
                  command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        
        # Enter-Key Binding
        self.dialog.bind('<Return>', lambda e: self.add_dryer())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def add_dryer(self):
        """Adds the new dryer"""
        name = self.name_var.get().strip()
        power_str = self.power_var.get().strip().replace(',', '.')
        
        if not name:
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.name_required"))
            return
        
        try:
            power = float(power_str)
            if power <= 0:
                raise ValueError(self.language_manager.t("messages.error.power_required"))
        except ValueError as ve:
            messagebox.showerror(self.language_manager.t("messages.error.title"), str(ve))
            return
        
        # Check if already exists
        if not self.dryer_manager.add_dryer(name, power):
            messagebox.showerror(self.language_manager.t("messages.error.title"), self.language_manager.t("messages.error.dryer_exists", name=name))
            return
        
        # Successfully added
        self.result = DryerType(name, power)
        messagebox.showinfo(self.language_manager.t("messages.success.title"), self.language_manager.t("messages.success.dryer_added", name=name))
        self.dialog.destroy()
    
    def cancel(self):
        """Cancels the dialog"""
        self.dialog.destroy()


class AboutDialog:
    """About dialog with app information, homepage link and donation button"""
    
    def __init__(self, parent, language_manager):
        self.parent = parent
        self.language_manager = language_manager
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.language_manager.t("dialogs.about.title"))
        self.dialog.geometry("490x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (490 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (350 // 2)
        self.dialog.geometry(f"490x350+{x}+{y}")
        
        self.setup_dialog()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_dialog(self):
        """Creates the about dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App icon
        try:
            # Try to load app icon
            if hasattr(sys, '_MEIPASS'):
                # Running as PyInstaller bundle
                icon_path = os.path.join(sys._MEIPASS, "assets", "icon.png")
            else:
                # Running as script
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
            
            if PIL_AVAILABLE and os.path.exists(icon_path):
                # Load and resize the image
                image = Image.open(icon_path)
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(image)
                
                icon_label = ttk.Label(main_frame, image=self.icon_photo)
                icon_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
                
                # App title
                app_title = ttk.Label(main_frame, text="3D-Print CostCulator", 
                                     font=("Arial", 16, "bold"))
                app_title.grid(row=1, column=0, columnspan=2, pady=(0, 5))
            else:
                # Fallback without icon
                app_title = ttk.Label(main_frame, text="3D-Print CostCulator", 
                                     font=("Arial", 16, "bold"))
                app_title.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        except Exception:
            # Any error, use simple title
            app_title = ttk.Label(main_frame, text="3D-Print CostCulator", 
                                 font=("Arial", 16, "bold"))
            app_title.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        version_label = ttk.Label(main_frame, text="Version 1.0", 
                                 font=("Arial", 10))
        version_label.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # App description
        description_text = self.language_manager.t("dialogs.about.description")
        description_label = ttk.Label(main_frame, text=description_text, 
                                     wraplength=400, justify=tk.CENTER)
        description_label.grid(row=3, column=0, columnspan=2, pady=(0, 20))
        
        # Copyright
        copyright_label = ttk.Label(main_frame, text="© 2025 xscr33mLabs", 
                                   font=("Arial", 10))
        copyright_label.grid(row=4, column=0, columnspan=2, pady=(0, 20))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))
        
        # Homepage button
        homepage_button = ttk.Button(button_frame, 
                                    text=self.language_manager.t("dialogs.about.homepage"), 
                                    command=self.open_homepage)
        homepage_button.pack(side=tk.LEFT, padx=5)
        
        # Donation button
        donation_button = ttk.Button(button_frame, 
                                    text=self.language_manager.t("dialogs.about.donate"), 
                                    command=self.open_donation)
        donation_button.pack(side=tk.LEFT, padx=5)
        
        # Source button
        source_button = ttk.Button(button_frame, 
                                    text=self.language_manager.t("dialogs.about.source"), 
                                    command=self.open_source)
        source_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, 
                                 text=self.language_manager.t("dialogs.about.close"), 
                                 command=self.close_dialog)
        close_button.pack(side=tk.LEFT, padx=5)
        
        # ESC key binding
        self.dialog.bind('<Escape>', lambda e: self.close_dialog())
    
    def open_homepage(self):
        """Opens the homepage in the default browser"""
        import webbrowser
        webbrowser.open("https://xscr33mlabs.com")
    
    def open_donation(self):
        """Opens the donation page in the default browser"""
        import webbrowser
        webbrowser.open("https://ko-fi.com/xscr33m")
    
    def open_source(self):
        """Opens the GitHub repository in the default browser"""
        import webbrowser
        webbrowser.open("https://github.com/xscr33m/3D-Print_CostCulator")
    
    def close_dialog(self):
        """Closes the dialog"""
        self.dialog.destroy()


class PrintCalculatorGUI:
    """Main class for the GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()

        self.root.geometry("700x650")

        self.root.resizable(False, False)
        
        # Set window icon
        self.set_window_icon()
        
        # Center window
        self.center_window()
        
        # Language Manager integration
        self.language_manager = language_manager
        self.language_manager.load_language_preference()
        self.language_manager.register_update_callback(self.update_gui_texts)
        
        # Configure button style
        self.setup_styles()
        
        # Initialize managers
        self.filament_manager = FilamentManager()
        self.printer_manager = PrinterManager()
        self.dryer_manager = DryerManager()
        
        # Current project
        self.current_project = PrintProject()
        self.current_file_path = None
        
        self.setup_ui()
        
        # Set initial language texts and update display after GUI is fully created
        self.root.after(100, lambda: [self.update_gui_texts(), self.update_display()])
    
    def setup_styles(self):
        """Configures the style themes for the buttons"""
        style = ttk.Style()
        
        style.configure('Calculate.TButton',
                       font=('Arial', 12, 'bold'))
        
    def set_window_icon(self):
        """Sets the window icon"""
        try:
            # Get the directory where the script is located
            if hasattr(sys, '_MEIPASS'):
                # Running as PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Running as script
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            icon_path = os.path.join(base_path, "assets", "icon.ico")
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                # Try alternative path for development
                dev_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
                if os.path.exists(dev_icon_path):
                    self.root.iconbitmap(dev_icon_path)
        except Exception as e:
            # Silently continue if icon can't be loaded
            print(f"Could not load icon: {e}")
    
    def center_window(self):
        """Centers the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        pos_x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    
    def toggle_language(self):
        """Switches between German and English"""
        current = self.language_manager.get_current_language()
        new_language = "en" if current == "de" else "de"
        self.language_manager.set_language(new_language)
        self.language_manager.save_language_preference()
    
    def update_language_button(self):
        """Updates the language button text"""
        current = self.language_manager.get_current_language()
        if current == "de":
            self.language_button.config(text=" DE ")
        else:
            self.language_button.config(text=" EN ")
    
    def update_gui_texts(self):
        """Updates all GUI texts after language change"""
        try:
            # Update window title
            base_title = self.language_manager.t("gui.window_title")
            if self.current_project.project_name:
                title = f"{base_title} - {self.current_project.project_name}"
            else:
                title = base_title
            if self.current_file_path:
                title += f" [{self.current_file_path}]"
            self.root.title(title)
            
            # Update language button
            if hasattr(self, 'language_button'):
                self.update_language_button()
            
            # Update buttons
            if hasattr(self, 'new_project_button'):
                self.new_project_button.config(text=self.language_manager.t("gui.buttons.new_project"))
            if hasattr(self, 'load_project_button'):
                self.load_project_button.config(text=self.language_manager.t("gui.menu.load_project"))
            if hasattr(self, 'save_project_button'):
                self.save_project_button.config(text=self.language_manager.t("gui.menu.save_project"))
            if hasattr(self, 'save_as_button'):
                self.save_as_button.config(text=self.language_manager.t("gui.menu.save_as"))
            if hasattr(self, 'export_pdf_button'):
                self.export_pdf_button.config(text=self.language_manager.t("gui.menu.export_pdf"))
            if hasattr(self, 'calculate_button'):
                self.calculate_button.config(text=self.language_manager.t("gui.buttons.calculate"))
            
            # Project frame and labels
            if hasattr(self, 'project_frame'):
                self.project_frame.config(text=self.language_manager.t("gui.project.title"))
            if hasattr(self, 'project_name_label'):
                self.project_name_label.config(text=self.language_manager.t("gui.project.name"))
            if hasattr(self, 'model_name_label'):
                self.model_name_label.config(text=self.language_manager.t("gui.project.model"))
            if hasattr(self, 'model_count_label'):
                self.model_count_label.config(text=self.language_manager.t("gui.project.model_count"))
            if hasattr(self, 'print_duration_label'):
                self.print_duration_label.config(text=self.language_manager.t("gui.project.print_duration"))
            
            # Material frame and labels
            if hasattr(self, 'filament_frame'):
                self.filament_frame.config(text=self.language_manager.t("gui.materials.title"))
            if hasattr(self, 'filament_label'):
                self.filament_label.config(text=self.language_manager.t("gui.materials.filament"))
            if hasattr(self, 'filament_cost_label'):
                self.filament_cost_label.config(text=self.language_manager.t("gui.materials.cost_per_kg"))
            if hasattr(self, 'filament_amount_label'):
                self.filament_amount_label.config(text=self.language_manager.t("gui.materials.amount"))
            
            # Printer frame and labels
            if hasattr(self, 'printer_frame'):
                self.printer_frame.config(text=self.language_manager.t("gui.printer.title"))
            if hasattr(self, 'printer_label'):
                self.printer_label.config(text=self.language_manager.t("gui.printer.printer"))
            if hasattr(self, 'printer_power_label'):
                self.printer_power_label.config(text=self.language_manager.t("gui.printer.power"))
            
            # Dryer frame and labels
            if hasattr(self, 'dryer_frame'):
                self.dryer_frame.config(text=self.language_manager.t("gui.dryer.title"))
            if hasattr(self, 'dryer_checkbox'):
                self.dryer_checkbox.config(text=self.language_manager.t("gui.dryer.enable"))
            if hasattr(self, 'dryer_label'):
                self.dryer_label.config(text=self.language_manager.t("gui.dryer.dryer"))
            if hasattr(self, 'dryer_power_label'):
                self.dryer_power_label.config(text=self.language_manager.t("gui.dryer.power"))
            
            # Cost frame and labels
            if hasattr(self, 'costs_frame'):
                self.costs_frame.config(text=self.language_manager.t("gui.electricity.title"))
            if hasattr(self, 'electricity_rate_label'):
                self.electricity_rate_label.config(text=self.language_manager.t("gui.electricity.rate"))
            if hasattr(self, 'wear_cost_label'):
                self.wear_cost_label.config(text=self.language_manager.t("gui.electricity.wear_cost"))
            
            # Update results
            if hasattr(self, 'result_frame'):
                self.result_frame.config(text=self.language_manager.t("gui.results.title"))
            if hasattr(self, 'individual_costs_label'):
                self.individual_costs_label.config(text=self.language_manager.t("gui.results.individual_costs"))
            if hasattr(self, 'total_costs_label'):
                self.total_costs_label.config(text=self.language_manager.t("gui.results.total_costs"))
            if hasattr(self, 'total_label'):
                self.total_label.config(text=self.language_manager.t("gui.results.total"))
            if hasattr(self, 'per_model_label'):
                self.per_model_label.config(text=self.language_manager.t("gui.results.cost_per_model"))
            if hasattr(self, 'filament_cost_title'):
                self.filament_cost_title.config(text=self.language_manager.t("gui.results.material_cost"))
            if hasattr(self, 'electricity_printer_title'):
                self.electricity_printer_title.config(text=self.language_manager.t("gui.results.electricity_printer"))
            if hasattr(self, 'electricity_dryer_title'):
                self.electricity_dryer_title.config(text=self.language_manager.t("gui.results.electricity_dryer"))
            if hasattr(self, 'wear_cost_title'):
                self.wear_cost_title.config(text=self.language_manager.t("gui.results.wear_cost"))
            
            # Update status
            if hasattr(self, 'status_var'):
                current_status = self.status_var.get()
                if "Bereit" in current_status or "Ready" in current_status:
                    self.status_var.set(self.language_manager.t("status.ready"))
                elif "Berechnung abgeschlossen" in current_status or "Calculation complete" in current_status:
                    # Status messages with dynamic content remain as they are
                    pass
                    
        except Exception as e:
            print(f"Error updating GUI texts: {e}")
    
    def update_button_states(self):
        """Updates the state of save/export buttons based on project status"""
        has_project = bool(self.current_project.project_name or 
                          self.current_project.model_name or 
                          self.current_file_path)
        
        # Enable/disable buttons based on project status
        state = "normal" if has_project else "disabled"
        
        if hasattr(self, 'save_project_button'):
            # Save button is only enabled if we have a current file path
            save_state = "normal" if self.current_file_path else "disabled"
            self.save_project_button.config(state=save_state)
        
        if hasattr(self, 'save_as_button'):
            self.save_as_button.config(state=state)
        
        if hasattr(self, 'export_pdf_button'):
            self.export_pdf_button.config(state=state)
    
    def setup_ui(self):
        """Creates the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid for perfect column alignment
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1, uniform="maincol")
        main_frame.columnconfigure(1, weight=1, uniform="maincol")
        
        # Menu frame with project buttons across full width
        menu_frame = ttk.Frame(main_frame)
        menu_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10), padx=5)
        
        # Configure grid columns for even distribution
        for i in range(6):  # 6 buttons total
            menu_frame.columnconfigure(i, weight=1)
        
        # Language button (leftmost)
        self.language_button = ttk.Button(menu_frame, text="🌐 DE", command=self.toggle_language)
        self.language_button.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=2)
        
        # Project action buttons (distributed across the row)
        self.new_project_button = ttk.Button(menu_frame, text=self.language_manager.t("gui.buttons.new_project"), 
                                           command=self.new_project)
        self.new_project_button.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        
        self.load_project_button = ttk.Button(menu_frame, text=self.language_manager.t("gui.menu.load_project"), 
                                            command=self.load_project)
        self.load_project_button.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=2)
        
        self.save_project_button = ttk.Button(menu_frame, text=self.language_manager.t("gui.menu.save_project"), 
                                            command=self.save_project, state="disabled")
        self.save_project_button.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=2)
        
        self.save_as_button = ttk.Button(menu_frame, text=self.language_manager.t("gui.menu.save_as"), 
                                       command=self.save_project_as, state="disabled")
        self.save_as_button.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=2)
        
        self.export_pdf_button = ttk.Button(menu_frame, text=self.language_manager.t("gui.menu.export_pdf"), 
                                          command=self.export_pdf, state="disabled")
        self.export_pdf_button.grid(row=0, column=5, sticky=(tk.W, tk.E), padx=2)
        
        # Keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_project())
        self.root.bind('<Control-o>', lambda e: self.load_project())
        self.root.bind('<Control-s>', lambda e: self.save_project())
        self.root.bind('<Control-S>', lambda e: self.save_project_as())  # Shift+S
        self.root.bind('<Control-e>', lambda e: self.export_pdf())
        
        # Input data displayed directly in main frame
        main_frame.rowconfigure(1, weight=1)
        self.setup_input_tab(main_frame)
        
        # Status Bar with info button
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0), padx=5)
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar()
        self.status_var.set(self.language_manager.t("status.ready"))
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Info button
        info_button = ttk.Button(status_frame, text="ℹ", width=3, command=self.show_about_dialog)
        info_button.grid(row=0, column=1, sticky=tk.E)
    
    def setup_input_tab(self, parent):
        """Creates the input tab"""
        # Uniform grid configuration for perfect alignment
        parent.columnconfigure(0, weight=1, uniform="col")
        parent.columnconfigure(1, weight=1, uniform="col")
        
        # Row configuration for uniform frame heights
        parent.rowconfigure(2, weight=1)  # Row 2 (Filament/Drucker)  
        parent.rowconfigure(3, weight=1)  # Row 3 (Kosten/Extras)
        
        # Project information
        self.project_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.project.title"), padding="10")
        self.project_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # StringVars for input fields
        self.vars = {}
        
        # Split project frame into two columns with different weights
        # Left column (Project Name, Model Name) gets more space
        self.project_frame.columnconfigure(0, weight=3)  # 60% width
        self.project_frame.columnconfigure(1, weight=2)  # 40% width
        
        # Left column
        left_project_frame = ttk.Frame(self.project_frame)
        left_project_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Project name (left)
        self.project_name_label = ttk.Label(left_project_frame, text=self.language_manager.t("gui.project.name"))
        self.project_name_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.vars['project_name'] = tk.StringVar()
        ttk.Entry(left_project_frame, textvariable=self.vars['project_name'], width=45).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        # 3D model (left)
        self.model_name_label = ttk.Label(left_project_frame, text=self.language_manager.t("gui.project.model"))
        self.model_name_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars['model_name'] = tk.StringVar()
        ttk.Entry(left_project_frame, textvariable=self.vars['model_name'], width=45).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        left_project_frame.columnconfigure(1, weight=1)
        
        # Right column
        right_project_frame = ttk.Frame(self.project_frame)
        right_project_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Model count (right)
        self.model_count_label = ttk.Label(right_project_frame, text=self.language_manager.t("gui.project.model_count"))
        self.model_count_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.vars['model_count'] = tk.StringVar(value="1")
        ttk.Entry(right_project_frame, textvariable=self.vars['model_count'], width=13).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        # Print duration (right)
        self.print_duration_label = ttk.Label(right_project_frame, text=self.language_manager.t("gui.project.print_duration"))
        self.print_duration_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars['print_duration'] = tk.StringVar()
        ttk.Entry(right_project_frame, textvariable=self.vars['print_duration'], width=13).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        right_project_frame.columnconfigure(1, weight=1)
        
        # Filament information
        self.filament_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.materials.title"), padding="10")
        self.filament_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        # Filament dropdown with add button
        filament_select_frame = ttk.Frame(self.filament_frame)
        filament_select_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        self.filament_label = ttk.Label(filament_select_frame, text=self.language_manager.t("gui.materials.filament"))
        self.filament_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.vars['filament_name'] = tk.StringVar()
        self.filament_combo = ttk.Combobox(filament_select_frame, textvariable=self.vars['filament_name'], 
                                          width=18, state="readonly")
        self.filament_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 5))
        self.filament_combo.bind('<<ComboboxSelected>>', self.on_filament_selected)
        
        # Button frame for + and - buttons
        button_frame = ttk.Frame(filament_select_frame)
        button_frame.grid(row=0, column=2, pady=2, padx=(5, 0))
        
        ttk.Button(button_frame, text="+", 
                  command=self.add_new_filament, width=2).grid(row=0, column=0, padx=(0, 2))
        
        self.remove_filament_button = ttk.Button(button_frame, text="−", 
                                               command=self.remove_filament, width=2, state="disabled")
        self.remove_filament_button.grid(row=0, column=1, padx=(2, 0))
        
        filament_select_frame.columnconfigure(1, weight=1)
        
        # Filament details (automatically filled)
        self.filament_cost_label = ttk.Label(self.filament_frame, text=self.language_manager.t("gui.materials.cost_per_kg"))
        self.filament_cost_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars['filament_cost_per_kg'] = tk.StringVar()
        self.filament_cost_entry = ttk.Entry(self.filament_frame, textvariable=self.vars['filament_cost_per_kg'], 
                                           width=25, state="readonly")
        self.filament_cost_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.filament_amount_label = ttk.Label(self.filament_frame, text=self.language_manager.t("gui.materials.amount"))
        self.filament_amount_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.vars['filament_amount'] = tk.StringVar()
        ttk.Entry(self.filament_frame, textvariable=self.vars['filament_amount'], width=25).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.filament_frame.columnconfigure(1, weight=1)
        
        # Initialize filament dropdown
        self.update_filament_combo()
        
        # Printer information
        self.printer_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.printer.title"), padding="10")
        self.printer_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        # Printer selection with buttons
        self.printer_label = ttk.Label(self.printer_frame, text=self.language_manager.t("gui.printer.printer"))
        self.printer_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        printer_select_frame = ttk.Frame(self.printer_frame)
        printer_select_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # Printer label in select frame
        ttk.Label(printer_select_frame, text=self.language_manager.t("gui.printer.printer")).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Printer dropdown
        self.vars['printer_name'] = tk.StringVar()
        self.printer_combo = ttk.Combobox(printer_select_frame, textvariable=self.vars['printer_name'], 
                                         state="readonly", width=18)
        self.printer_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 5))
        self.printer_combo.bind('<<ComboboxSelected>>', self.on_printer_selected)
        
        # Button frame for Add/Remove buttons
        button_frame = ttk.Frame(printer_select_frame)
        button_frame.grid(row=0, column=2, pady=2, padx=(5, 0))
        
        ttk.Button(button_frame, text="+", 
                  command=self.add_new_printer, width=2).grid(row=0, column=0, padx=(0, 2))
        
        self.remove_printer_button = ttk.Button(button_frame, text="−", 
                                               command=self.remove_printer, width=2, state="disabled")
        self.remove_printer_button.grid(row=0, column=1, padx=(2, 0))
        
        printer_select_frame.columnconfigure(1, weight=1)
        
        # Printer power (automatically filled)
        self.printer_power_label = ttk.Label(self.printer_frame, text=self.language_manager.t("gui.printer.power"))
        self.printer_power_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars['printer_power'] = tk.StringVar()
        power_entry = ttk.Entry(self.printer_frame, textvariable=self.vars['printer_power'], width=25, state="readonly")
        power_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.printer_frame.columnconfigure(1, weight=1)
        
        # Initialize printer dropdown
        self.update_printer_combo()
        
        # Optional additional devices
        self.dryer_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.dryer.title"), padding="10")
        self.dryer_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        self.vars['dryer_enabled'] = tk.BooleanVar()
        self.dryer_checkbox = ttk.Checkbutton(self.dryer_frame, text=self.language_manager.t("gui.dryer.enable"), 
                       variable=self.vars['dryer_enabled'],
                       command=self.toggle_dryer)
        self.dryer_checkbox.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Dryer selection with buttons
        self.dryer_label = ttk.Label(self.dryer_frame, text=self.language_manager.t("gui.dryer.dryer"))
        self.dryer_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        dryer_select_frame = ttk.Frame(self.dryer_frame)
        dryer_select_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # Dryer label in select frame
        ttk.Label(dryer_select_frame, text=self.language_manager.t("gui.dryer.dryer")).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Dryer dropdown
        self.vars['dryer_name'] = tk.StringVar()
        self.dryer_combo = ttk.Combobox(dryer_select_frame, textvariable=self.vars['dryer_name'], 
                                       state="disabled", width=18)
        self.dryer_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 5))
        self.dryer_combo.bind('<<ComboboxSelected>>', self.on_dryer_selected)
        
        # Button frame for Add/Remove buttons
        dryer_button_frame = ttk.Frame(dryer_select_frame)
        dryer_button_frame.grid(row=0, column=2, pady=2, padx=(5, 0))
        
        self.add_dryer_button = ttk.Button(dryer_button_frame, text="+", 
                                         command=self.add_new_dryer, width=2, state="disabled")
        self.add_dryer_button.grid(row=0, column=0, padx=(0, 2))
        
        self.remove_dryer_button = ttk.Button(dryer_button_frame, text="−", 
                                            command=self.remove_dryer, width=2, state="disabled")
        self.remove_dryer_button.grid(row=0, column=1, padx=(2, 0))
        
        dryer_select_frame.columnconfigure(1, weight=1)
        
        # Dryer power (automatically filled)
        self.dryer_power_label = ttk.Label(self.dryer_frame, text=self.language_manager.t("gui.dryer.power"))
        self.dryer_power_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.vars['dryer_power'] = tk.StringVar()
        self.dryer_power_entry = ttk.Entry(self.dryer_frame, textvariable=self.vars['dryer_power'], 
                                          width=25, state="disabled")
        self.dryer_power_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.dryer_frame.columnconfigure(1, weight=1)
        
        # Initialize dryer dropdown
        self.update_dryer_combo()
        
        # Cost section
        self.costs_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.electricity.title"), padding="10")
        self.costs_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        self.electricity_rate_label = ttk.Label(self.costs_frame, text=self.language_manager.t("gui.electricity.rate"))
        self.electricity_rate_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.vars['electricity_cost'] = tk.StringVar()
        ttk.Entry(self.costs_frame, textvariable=self.vars['electricity_cost'], width=25).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.wear_cost_label = ttk.Label(self.costs_frame, text=self.language_manager.t("gui.electricity.wear_cost"))
        self.wear_cost_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vars['wear_cost_display'] = tk.StringVar(value=self.language_manager.t("gui.status.please_calculate"))
        wear_display = ttk.Label(self.costs_frame, textvariable=self.vars['wear_cost_display'], 
                               foreground="black", font=("Arial", 9))
        wear_display.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.costs_frame.columnconfigure(1, weight=1)
        
        # Cost overview directly after input fields
        self.setup_result_section(parent, start_row=4)
        
        # Bind Enter key for automatic calculation
        for var in self.vars.values():
            if isinstance(var, tk.StringVar):
                var.trace_add('write', self.on_input_change)
    
    def setup_result_section(self, parent, start_row=0):
        """Creates the cost overview section"""
        # Calculate button frame (above results)
        calculate_frame = ttk.Frame(parent)
        calculate_frame.grid(row=start_row, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(5, 10))
        
        # Calculate button - centered and prominent
        self.calculate_button = ttk.Button(calculate_frame, text=self.language_manager.t("gui.buttons.calculate"), 
                                         command=self.calculate_costs, style='Calculate.TButton')
        self.calculate_button.pack(expand=True, pady=5)
        
        # Result frame
        self.result_frame = ttk.LabelFrame(parent, text=self.language_manager.t("gui.results.title"), padding="10")
        self.result_frame.grid(row=start_row+1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(0, 0))
        
        # Result labels
        self.result_labels = {}
        
        # Two columns for better clarity
        left_frame = ttk.Frame(self.result_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        
        right_frame = ttk.Frame(self.result_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N))
        
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.columnconfigure(1, weight=2)
        
        # Left column - individual costs
        self.individual_costs_label = ttk.Label(left_frame, text=self.language_manager.t("gui.results.individual_costs"), font=("Arial", 11, "bold"))
        self.individual_costs_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        self.filament_cost_title = ttk.Label(left_frame, text=self.language_manager.t("gui.results.material_cost"))
        self.filament_cost_title.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.result_labels['filament_cost'] = ttk.Label(left_frame, text="--", foreground="gray")
        self.result_labels['filament_cost'].grid(row=1, column=1, sticky=tk.E, pady=2)
        
        self.electricity_printer_title = ttk.Label(left_frame, text=self.language_manager.t("gui.results.electricity_printer"))
        self.electricity_printer_title.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.result_labels['electricity_cost_printer'] = ttk.Label(left_frame, text="--", foreground="gray")
        self.result_labels['electricity_cost_printer'].grid(row=2, column=1, sticky=tk.E, pady=2)
        
        self.electricity_dryer_title = ttk.Label(left_frame, text=self.language_manager.t("gui.results.electricity_dryer"))
        self.electricity_dryer_title.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.result_labels['electricity_cost_dryer'] = ttk.Label(left_frame, text="--", foreground="gray")
        self.result_labels['electricity_cost_dryer'].grid(row=3, column=1, sticky=tk.E, pady=2)
        
        self.wear_cost_title = ttk.Label(left_frame, text=self.language_manager.t("gui.results.wear_cost"))
        self.wear_cost_title.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.result_labels['wear_cost'] = ttk.Label(left_frame, text="--", foreground="gray")
        self.result_labels['wear_cost'].grid(row=4, column=1, sticky=tk.E, pady=2)
        
        left_frame.columnconfigure(1, weight=1)
        
        # Right column - total costs
        self.total_costs_label = ttk.Label(right_frame, text=self.language_manager.t("gui.results.total_costs"), font=("Arial", 11, "bold"))
        self.total_costs_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Total costs with background
        total_frame = ttk.Frame(right_frame, relief="solid", borderwidth=1)
        total_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        total_frame.configure(style="TFrame")
        
        self.total_label = ttk.Label(total_frame, text=self.language_manager.t("gui.results.total"), font=("Arial", 12, "bold"))
        self.total_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=8)
        self.result_labels['total_cost'] = ttk.Label(total_frame, text=self.language_manager.t("gui.status.please_calculate"), font=("Arial", 12, "bold"), foreground="gray")
        self.result_labels['total_cost'].grid(row=0, column=1, sticky=tk.E, padx=10, pady=8)
        total_frame.columnconfigure(1, weight=1)
        
        # Cost per model
        self.per_model_label = ttk.Label(right_frame, text=self.language_manager.t("gui.results.cost_per_model"), font=("Arial", 10))
        self.per_model_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        self.result_labels['cost_per_model'] = ttk.Label(right_frame, text=self.language_manager.t("gui.status.please_calculate"), font=("Arial", 10), foreground="gray")
        self.result_labels['cost_per_model'].grid(row=2, column=1, sticky=tk.E, pady=(10, 2))
        
        right_frame.columnconfigure(1, weight=1)
    
    def update_filament_combo(self):
        """Updates the filament dropdown list"""
        filament_names = self.filament_manager.get_filament_names()
        self.filament_combo['values'] = filament_names
        
        # Select first entry by default, if available
        if filament_names:
            current_selection = self.vars['filament_name'].get()
            if not current_selection or current_selection not in filament_names:
                self.vars['filament_name'].set(filament_names[0])
                self.on_filament_selected()  # Update price
            # Enable remove button
            self.remove_filament_button.config(state="normal")
        else:
            self.vars['filament_name'].set('')
            # Disable remove button
            self.remove_filament_button.config(state="disabled")
    
    def on_filament_selected(self, event=None):
        """Called when a filament is selected"""
        selected_name = self.vars['filament_name'].get()
        filament = self.filament_manager.get_filament_by_name(selected_name)
        if filament:
            self.vars['filament_cost_per_kg'].set(str(filament.cost_per_kg))
    
    def add_new_filament(self):
        """Dialog for adding a new filament"""
        dialog = FilamentDialog(self.root, self.filament_manager, self.language_manager)
        if dialog.result:
            self.update_filament_combo()
            # Select new filament
            self.vars['filament_name'].set(dialog.result.name)
            self.on_filament_selected()
    
    def remove_filament(self):
        """Removes the currently selected filament"""
        selected_name = self.vars['filament_name'].get()
        if not selected_name:
            tk.messagebox.showwarning(self.language_manager.t("messages.error.title"), 
                                    self.language_manager.t("messages.error.select_filament_first"))
            return
        
        # Confirmation from user
        if tk.messagebox.askyesno(self.language_manager.t("messages.confirmation.remove_filament_title"), 
                                 self.language_manager.t("messages.confirmation.remove_filament_message", name=selected_name)):
            self.filament_manager.remove_filament(selected_name)
            self.update_filament_combo()
            
            # Check if filaments are still available
            filament_names = self.filament_manager.get_filament_names()
            if not filament_names:
                self.remove_filament_button.config(state="disabled")
                self.vars['filament_cost_per_kg'].set("")
    
    def update_printer_combo(self):
        """Updates the printer dropdown list"""
        printer_names = self.printer_manager.get_printer_names()
        self.printer_combo['values'] = printer_names
        
        # Select first entry by default, if available
        if printer_names:
            current_selection = self.vars['printer_name'].get()
            if not current_selection or current_selection not in printer_names:
                self.vars['printer_name'].set(printer_names[0])
                self.on_printer_selected()  # Update power
            # Enable remove button
            self.remove_printer_button.config(state="normal")
        else:
            self.vars['printer_name'].set('')
            # Disable remove button
            self.remove_printer_button.config(state="disabled")
    
    def on_printer_selected(self, event=None):
        """Called when a printer is selected"""
        selected_name = self.vars['printer_name'].get()
        printer = self.printer_manager.get_printer_by_name(selected_name)
        if printer:
            self.vars['printer_power'].set(str(printer.power))
    
    def add_new_printer(self):
        """Dialog for adding a new printer"""
        dialog = PrinterDialog(self.root, self.printer_manager, self.language_manager)
        if dialog.result:
            self.update_printer_combo()
            # Select new printer
            self.vars['printer_name'].set(dialog.result.name)
            self.on_printer_selected()
    
    def remove_printer(self):
        """Removes the currently selected printer"""
        selected_name = self.vars['printer_name'].get()
        if not selected_name:
            tk.messagebox.showwarning(self.language_manager.t("messages.error.title"), 
                                    self.language_manager.t("messages.error.select_printer_first"))
            return
        
        # Confirmation from user
        if tk.messagebox.askyesno(self.language_manager.t("messages.confirmation.remove_printer_title"), 
                                 self.language_manager.t("messages.confirmation.remove_printer_message", name=selected_name)):
            self.printer_manager.remove_printer(selected_name)
            self.update_printer_combo()
            
            # Check if printers are still available
            printer_names = self.printer_manager.get_printer_names()
            if not printer_names:
                self.remove_printer_button.config(state="disabled")
                self.vars['printer_power'].set("")
    
    def update_dryer_combo(self):
        """Updates the dryer dropdown list"""
        dryer_names = self.dryer_manager.get_dryer_names()
        self.dryer_combo['values'] = dryer_names
        
    # Select first entry by default, if available
        if dryer_names:
            current_selection = self.vars['dryer_name'].get()
            if not current_selection or current_selection not in dryer_names:
                self.vars['dryer_name'].set(dryer_names[0])
                self.on_dryer_selected()  # Update power
            # Enable remove button if dryer is enabled
            if self.vars['dryer_enabled'].get():
                self.remove_dryer_button.config(state="normal")
        else:
            self.vars['dryer_name'].set('')
            # Disable remove button
            self.remove_dryer_button.config(state="disabled")
    
    def on_dryer_selected(self, event=None):
        """Called when a dryer is selected"""
        selected_name = self.vars['dryer_name'].get()
        dryer = self.dryer_manager.get_dryer_by_name(selected_name)
        if dryer:
            self.vars['dryer_power'].set(str(dryer.power))
    
    def add_new_dryer(self):
        """Dialog for adding a new dryer"""
        dialog = DryerDialog(self.root, self.dryer_manager, self.language_manager)
        if dialog.result:
            self.update_dryer_combo()
            # Select new dryer
            self.vars['dryer_name'].set(dialog.result.name)
            self.on_dryer_selected()
    
    def remove_dryer(self):
        """Removes the currently selected dryer"""
        selected_name = self.vars['dryer_name'].get()
        if not selected_name:
            tk.messagebox.showwarning(self.language_manager.t("messages.error.title"), 
                                    self.language_manager.t("messages.error.select_dryer_first"))
            return
        
    # Confirmation from user
        if tk.messagebox.askyesno(self.language_manager.t("messages.confirmation.remove_dryer_title"), 
                                 self.language_manager.t("messages.confirmation.remove_dryer_message", name=selected_name)):
            self.dryer_manager.remove_dryer(selected_name)
            self.update_dryer_combo()
            
            # Check if dryers are still available
            dryer_names = self.dryer_manager.get_dryer_names()
            if not dryer_names:
                self.remove_dryer_button.config(state="disabled")
                self.vars['dryer_power'].set("")
    
    def update_display(self):
        """Updates the display of calculated costs"""
        # Update result labels
        if hasattr(self, 'result_labels'):
            # Update values and colors
            self.result_labels['filament_cost'].config(
                text=f"{self.current_project.filament_cost:.4f} €", 
                foreground="blue" if self.current_project.filament_cost > 0 else "gray"
            )
            self.result_labels['electricity_cost_printer'].config(
                text=f"{self.current_project.electricity_cost_printer:.4f} €", 
                foreground="blue" if self.current_project.electricity_cost_printer > 0 else "gray"
            )
            self.result_labels['electricity_cost_dryer'].config(
                text=f"{self.current_project.electricity_cost_dryer:.4f} €", 
                foreground="blue" if self.current_project.electricity_cost_dryer > 0 else "gray"
            )
            self.result_labels['wear_cost'].config(
                text=f"{self.current_project.wear_cost:.4f} €", 
                foreground="blue" if self.current_project.wear_cost > 0 else "gray"
            )
            self.result_labels['total_cost'].config(
                text=f"{self.current_project.total_cost:.4f} €", 
                foreground="darkgreen" if self.current_project.total_cost > 0 else "gray"
            )
            
            # Update wear display in cost section
            if hasattr(self, 'vars') and 'wear_cost_display' in self.vars:
                self.vars['wear_cost_display'].set(f"{self.current_project.wear_cost:.4f} €")
            
            # Cost per model
            cost_per_model = self.current_project.total_cost / max(1, self.current_project.model_count)
            self.result_labels['cost_per_model'].config(
                text=f"{cost_per_model:.4f} €", 
                foreground="darkgreen" if cost_per_model > 0 else "gray"
            )
        
        # Update window title
        title = "3D-Print CostCulator v1.0"
        if self.current_project.project_name:
            title += f" - {self.current_project.project_name}"
        if self.current_file_path:
            title += f" ({os.path.basename(self.current_file_path)})"
        self.root.title(title)
        
        # Update button states
        self.update_button_states()
        
        # Force update the display
        self.root.update_idletasks()
    
    def load_project_data(self):
        """Loads current project data into the GUI fields"""
        if hasattr(self, 'vars'):
            self.vars['project_name'].set(self.current_project.project_name)
            self.vars['model_name'].set(self.current_project.model_name)
            self.vars['model_count'].set(str(self.current_project.model_count))
            self.vars['print_duration'].set(str(self.current_project.print_duration))
            self.vars['filament_name'].set(self.current_project.filament_name)
            self.vars['filament_amount'].set(str(self.current_project.filament_amount))
            self.vars['filament_cost_per_kg'].set(str(self.current_project.filament_cost_per_kg))
            self.vars['printer_name'].set(self.current_project.printer_name)  # Newly added
            self.vars['printer_power'].set(str(self.current_project.printer_power))
            self.vars['electricity_cost'].set(str(self.current_project.electricity_cost))
            self.vars['dryer_enabled'].set(self.current_project.dryer_enabled)
            self.vars['dryer_name'].set(self.current_project.dryer_name)
            self.vars['dryer_power'].set(str(self.current_project.dryer_power))
            
            self.toggle_dryer()  # Update dryer field state
            self.on_filament_selected()  # Update filament cost field
            self.on_printer_selected()  # Update printer power field
            self.on_dryer_selected()  # Update dryer power field
    
    def save_project_data(self):
        """Saves GUI data to the current project"""
        try:
            if hasattr(self, 'vars'):
                # Validate and set project data
                self.current_project.project_name = self.vars['project_name'].get().strip()
                self.current_project.model_name = self.vars['model_name'].get().strip()
                
                # Validate numeric inputs
                model_count_str = self.vars['model_count'].get().strip()
                if model_count_str:
                    model_count = int(model_count_str)
                    if model_count < 1:
                        raise ValueError(self.language_manager.t("messages.error.model_count_invalid"))
                    self.current_project.model_count = model_count
                else:
                    self.current_project.model_count = 1
                
                # Print duration
                duration_str = self.vars['print_duration'].get().strip()
                if duration_str:
                    duration = float(duration_str.replace(',', '.'))
                    if duration < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.project.print_duration")))
                    self.current_project.print_duration = duration
                else:
                    self.current_project.print_duration = 0.0
                
                self.current_project.filament_name = self.vars['filament_name'].get().strip()
                
                # Filament amount
                amount_str = self.vars['filament_amount'].get().strip()
                if amount_str:
                    amount = float(amount_str.replace(',', '.'))
                    if amount < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.materials.amount")))
                    self.current_project.filament_amount = amount
                else:
                    self.current_project.filament_amount = 0.0
                
                # Filament costs
                cost_str = self.vars['filament_cost_per_kg'].get().strip()
                if cost_str:
                    cost = float(cost_str.replace(',', '.'))
                    if cost < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.materials.cost_per_kg")))
                    self.current_project.filament_cost_per_kg = cost
                else:
                    self.current_project.filament_cost_per_kg = 0.0
                
                # Printer name
                self.current_project.printer_name = self.vars['printer_name'].get().strip()
                
                # Printer power
                power_str = self.vars['printer_power'].get().strip()
                if power_str:
                    power = float(power_str.replace(',', '.'))
                    if power < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.printer.power")))
                    self.current_project.printer_power = power
                else:
                    self.current_project.printer_power = 0.0
                
                # Electricity costs
                elec_str = self.vars['electricity_cost'].get().strip()
                if elec_str:
                    elec_cost = float(elec_str.replace(',', '.'))
                    if elec_cost < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.electricity.rate")))
                    self.current_project.electricity_cost = elec_cost
                else:
                    self.current_project.electricity_cost = 0.0
                
                self.current_project.dryer_enabled = self.vars['dryer_enabled'].get()
                
                # Dryer name
                self.current_project.dryer_name = self.vars['dryer_name'].get().strip()
                
                # Dryer power
                dryer_power_str = self.vars['dryer_power'].get().strip()
                if dryer_power_str:
                    dryer_power = float(dryer_power_str.replace(',', '.'))
                    if dryer_power < 0:
                        raise ValueError(self.language_manager.t("messages.validation.negative_value", field=self.language_manager.t("gui.dryer.power")))
                    self.current_project.dryer_power = dryer_power
                else:
                    self.current_project.dryer_power = 0.0
                
                # Set wear_cost_percent to 0 (not used anymore since it's calculated automatically)
                self.current_project.wear_cost_percent = 0.0
                    
        except ValueError as e:
            messagebox.showerror(self.language_manager.t("messages.error.title"), f"{self.language_manager.t('messages.error.invalid_input')}: {str(e)}")
            return False
        except Exception as e:
            messagebox.showerror(self.language_manager.t("messages.error.title"), f"{self.language_manager.t('messages.error.save_error')}: {str(e)}")
            return False
        return True
    
    def validate_required_fields(self):
        """Checks if all required fields are filled"""
        errors = []
        
        if not self.current_project.project_name:
            errors.append(self.language_manager.t("messages.error.project_name_required"))
        
        if not self.current_project.model_name:
            errors.append(self.language_manager.t("messages.error.model_name_required"))
        
        if self.current_project.print_duration <= 0:
            errors.append(self.language_manager.t("messages.error.print_duration_invalid"))
        
        if self.current_project.filament_amount <= 0:
            errors.append(self.language_manager.t("messages.error.filament_amount_invalid"))
        
        if self.current_project.filament_cost_per_kg <= 0:
            errors.append(self.language_manager.t("messages.error.cost_required"))
        
        if self.current_project.printer_power <= 0:
            errors.append(self.language_manager.t("messages.error.power_required"))
        
        if self.current_project.electricity_cost <= 0:
            errors.append(self.language_manager.t("messages.error.electricity_rate_invalid"))
        
        if self.current_project.dryer_enabled and self.current_project.dryer_power <= 0:
            errors.append(self.language_manager.t("messages.error.power_required"))
        
        return errors
    
    def toggle_dryer(self):
        """Enables/disables the dryer input field and buttons"""
        enabled = self.vars['dryer_enabled'].get()
        
        if hasattr(self, 'dryer_power_entry'):
            if enabled:
                self.dryer_power_entry.config(state="readonly")
                self.dryer_combo.config(state="readonly")
                self.add_dryer_button.config(state="normal")
                # Only enable remove button if dryer is selected
                dryer_names = self.dryer_manager.get_dryer_names()
                if dryer_names and self.vars['dryer_name'].get():
                    self.remove_dryer_button.config(state="normal")
            else:
                self.dryer_power_entry.config(state="disabled")
                self.dryer_combo.config(state="disabled")
                self.add_dryer_button.config(state="disabled")
                self.remove_dryer_button.config(state="disabled")
    
    def on_input_change(self, *args):
        """Called when an input value changes"""
        # Auto-calculate when input changes (with delay to avoid constant calculation)
        pass
    
    def calculate_costs(self):
        """Calculates the costs for the current project"""
        if not self.save_project_data():
            return
        
    # Validate required fields
        validation_errors = self.validate_required_fields()
        if validation_errors:
            error_message = self.language_manager.t("messages.error.invalid_input") + ":\n\n" + "\n".join(f"• {error}" for error in validation_errors)
            messagebox.showerror(self.language_manager.t("messages.error.title"), error_message)
            return
        
        try:
            # Perform calculation
            self.current_project = CostCulator.calculate_total_costs(self.current_project)
            
            # Update display
            self.update_display()
            
            # Success highlight: briefly highlight total cost
            original_color = self.result_labels['total_cost'].cget('foreground')
            self.result_labels['total_cost'].config(foreground='green')
            self.root.after(1500, lambda: self.result_labels['total_cost'].config(foreground=original_color))
            
            self.status_var.set(self.language_manager.t("status.calculation_complete", cost=f"{self.current_project.total_cost:.4f}"))
        except Exception as e:
            messagebox.showerror(self.language_manager.t("messages.error.title"), 
                                f"{self.language_manager.t('messages.error.calculation_error')}: {str(e)}")
            self.status_var.set(self.language_manager.t("status.calculation_error"))
    
    def new_project(self):
        """Creates a new project"""
        if messagebox.askyesno(self.language_manager.t("messages.confirmation.new_project_title"), 
                              self.language_manager.t("messages.confirmation.new_project_message")):
            self.current_project = PrintProject()
            self.current_file_path = None
            self.load_project_data()
            self.update_display()
            self.status_var.set(self.language_manager.t("status.new_project_created"))
    
    def load_project(self):
        """Loads a project from a file"""
        file_path = filedialog.askopenfilename(
            title=self.language_manager.t("file_dialogs.load_project_title"),
            filetypes=[(self.language_manager.t("file_dialogs.json_files"), "*.json"), 
                      (self.language_manager.t("file_dialogs.all_files"), "*.*")],
            defaultextension=".json"
        )
        
        if file_path:
            project = ProjectManager.load_project(file_path)
            if project:
                self.current_project = project
                self.current_file_path = file_path
                self.load_project_data()
                
                # Automatically calculate costs if data already exists
                if self.current_project.total_cost > 0:
                    self.current_project = CostCulator.calculate_total_costs(self.current_project)
                
                self.update_display()
                self.status_var.set(self.language_manager.t("status.project_loaded", filename=os.path.basename(file_path)))
    
    def save_project(self):
        """Saves the current project"""
        if not self.current_file_path:
            self.save_project_as()
            return
        
        if not self.save_project_data():
            return
        
        if ProjectManager.save_project(self.current_project, self.current_file_path):
            self.status_var.set(self.language_manager.t("status.project_saved", filename=os.path.basename(self.current_file_path)))
    
    def save_project_as(self):
        """Saves the current project under a new name"""
        if not self.save_project_data():
            return
        
        file_path = filedialog.asksaveasfilename(
            title=self.language_manager.t("file_dialogs.save_project_title"),
            filetypes=[(self.language_manager.t("file_dialogs.json_files"), "*.json"), 
                      (self.language_manager.t("file_dialogs.all_files"), "*.*")],
            defaultextension=".json",
            initialfile=f"{self.current_project.project_name or self.language_manager.t('file_dialogs.unnamed')}.json"
        )
        
        if file_path:
            if ProjectManager.save_project(self.current_project, file_path):
                self.current_file_path = file_path
                self.update_display()
                self.status_var.set(self.language_manager.t("status.project_saved", filename=os.path.basename(file_path)))
    
    def export_pdf(self):
        """Exports the costs as PDF"""
        if not self.save_project_data():
            return
        
    # Calculate costs before export
        self.current_project = CostCulator.calculate_total_costs(self.current_project)
        
        file_path = filedialog.asksaveasfilename(
            title=self.language_manager.t("file_dialogs.export_pdf_title"),
            filetypes=[(self.language_manager.t("file_dialogs.pdf_files"), "*.pdf"), 
                      (self.language_manager.t("file_dialogs.all_files"), "*.*")],
            defaultextension=".pdf",
            initialfile=f"{self.current_project.project_name or self.language_manager.t('file_dialogs.cost_calculation')}.pdf"
        )
        
        if file_path:
            if PDFExporter.export_to_pdf(self.current_project, file_path, self.language_manager):
                self.status_var.set(self.language_manager.t("status.pdf_exported", filename=os.path.basename(file_path)))
                if messagebox.askyesno(self.language_manager.t("messages.confirmation.pdf_created_title"), 
                                     self.language_manager.t("messages.confirmation.pdf_created_message", filepath=file_path)):
                    try:
                        os.startfile(file_path)  # Windows
                    except AttributeError:
                        import subprocess
                        subprocess.run(['open', file_path])  # macOS/Linux
    
    def show_about_dialog(self):
        """Shows the about dialog"""
        AboutDialog(self.root, self.language_manager)
    
    def create_tooltip(self, widget, text):
        """Creates a simple tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.configure(bg="lightyellow", relief="solid", borderwidth=1)
            
            label = ttk.Label(tooltip, text=text, background="lightyellow", 
                             font=("Arial", 9))
            label.pack()
            
            # Position tooltip near mouse
            x = event.x_root + 10
            y = event.y_root + 10
            tooltip.geometry(f"+{x}+{y}")
            
            # Store tooltip reference to hide it later
            widget._tooltip = tooltip
            
            # Hide tooltip after 3 seconds
            tooltip.after(3000, tooltip.destroy)
        
        def hide_tooltip(event):
            if hasattr(widget, '_tooltip') and widget._tooltip:
                try:
                    widget._tooltip.destroy()
                except:
                    pass
                widget._tooltip = None
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def run(self):
        """Starts the GUI application"""
        self.root.mainloop()


def main():
    """Main function"""
    app = PrintCalculatorGUI()
    app.run()


if __name__ == "__main__":
    main()