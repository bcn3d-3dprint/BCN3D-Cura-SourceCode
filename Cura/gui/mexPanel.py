__author__ = 'rmelbourne'

import wx
import ConfigParser as configparser
import os.path

from Cura.util import profile
from Cura.util import resources

class ProfileInfo(object):
	def __init__(self, filename):
		self.filename = filename
		self.base_filename = os.path.splitext(os.path.basename(filename))[0]
		cp = configparser.ConfigParser()
		cp.read(filename)

		self.name = self.base_filename
		self.material = None
		self.extruder_name = None
		self.order = 0

		if cp.has_option('info', 'name'):
			self.name = cp.get('info', 'name')
		if cp.has_option('info', 'material'):
			self.material = cp.get('info', 'material')
		if cp.has_option('info', 'extruder_name'):
			self.extruder_name = cp.get('info', 'extruder_name')
		if cp.has_option('info', 'extruder_name'):
			self.order = int(cp.get('info', 'order'))

class ProfileManager(object):
	def __init__(self):
		self._print_profiles = []
		self._material_profiles = []
		self._material_in_print_profile = False
		for filename in resources.getSimpleModeProfiles(profile.getMachineSetting('machine_type')):
			pi = ProfileInfo(filename)
			self._print_profiles.append(pi)
			if pi.material is not None:
				self._material_in_print_profile = True

		if not self._material_in_print_profile and profile.getMachineSetting('gcode_flavor') != 'UltiGCode':
			for filename in resources.getSimpleModeMaterials():
				pi = ProfileInfo(filename)
				self._material_profiles.append(pi)

		self._print_profiles.sort(cmp=lambda a, b: a.order - b.order)
		self._material_profiles.sort(cmp=lambda a, b: a.order - b.order)

	def getProfileNames(self):
		ret = []
		for profile in self._print_profiles:
			if profile.name not in ret:
				ret.append(profile.name)
		return ret

	def getMaterialNames(self):
		ret = []
		if self._material_in_print_profile:
			for profile in self._print_profiles:
				if profile.material is not None and profile.material not in ret:
					ret.append(profile.material)
		else:
			for profile in self._material_profiles:
				if profile.name not in ret:
					ret.append(profile.name)
		return ret

	def getExtruderNames(self):
		ret = []
		for profile in self._print_profiles:
			if profile.extruder_name is not None and profile.extruder_name not in ret:
				ret.append(profile.extruder_name)
		return ret

	def isValidProfileOption(self, profile_name, material_name, extruder_name):
		return self._getProfileFor(profile_name, material_name, extruder_name) is not None

	def getSettingsFor(self, profile_name, material_name, extruder_name):
		settings = {}

		current_profile = self._getProfileFor(profile_name, material_name, extruder_name)
		cp = configparser.ConfigParser()
		cp.read(current_profile.filename)
		for setting in profile.settingsList:
			if setting.isProfile():
				if cp.has_option('profile', setting.getName()):
					settings[setting.getName()] = cp.get('profile', setting.getName())

		if not self._material_in_print_profile:
			for current_profile in self._material_profiles:
				if current_profile.name == material_name:
					cp = configparser.ConfigParser()
					cp.read(current_profile.filename)
					for setting in profile.settingsList:
						if setting.isProfile():
							if cp.has_option('profile', setting.getName()):
								settings[setting.getName()] = cp.get('profile', setting.getName())

		return settings

	def _getProfileFor(self, profile_name, material_name, extruder_name):
		if self._material_in_print_profile:
			for profile in self._print_profiles:
				if profile.name == profile_name and profile.material == material_name and extruder_name == profile.extruder_name:
					return profile
		else:
			for profile in self._print_profiles:
				if profile.name == profile_name and extruder_name == profile.extruder_name:
					return profile
		return None

class MexPanel(wx.Panel):
	"Mono extruder quickprint mode"
	def __init__(self, parent, callback):
		super(MexPanel, self).__init__(parent)

		self._callback = callback

		self._profile_manager = ProfileManager()

		self._print_profile_options = []
		self._print_material_options = []
		self._print_extruder_options = []

		printExtruderPanel = wx.Panel(self)
		for name in self._profile_manager.getExtruderNames():
			button = wx.RadioButton(printExtruderPanel, -1, name, style=wx.RB_GROUP if len(self._print_extruder_options) == 0 else 0)
			button.name = name
			self._print_extruder_options.append(button)
			if profile.getPreference('simpleModeExtruder') == name:
				button.SetValue(True)

		printMaterialPanel = wx.Panel(self)
		for name in self._profile_manager.getMaterialNames():
			button = wx.RadioButton(printMaterialPanel, -1, name, style=wx.RB_GROUP if len(self._print_material_options) == 0 else 0)
			button.name = name
			self._print_material_options.append(button)
			if profile.getPreference('simpleModeMaterial') == name:
				button.SetValue(True)

		printTypePanel = wx.Panel(self)
		for name in self._profile_manager.getProfileNames():
			button = wx.RadioButton(printTypePanel, -1, name, style=wx.RB_GROUP if len(self._print_profile_options) == 0 else 0)
			button.name = name
			self._print_profile_options.append(button)
			if profile.getPreference('simpleModeProfile') == name:
				button.SetValue(True)

		if len(self._print_extruder_options) < 1:
			printExtruderPanel.Show(False)
		if len(self._print_material_options) < 1:
			printMaterialPanel.Show(False)

		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))
		self.platform_adhesion_panel = wx.Panel(self)
		self.platform_adhesion_label = wx.StaticText(self.platform_adhesion_panel, -1, _("Platform adhesion"))
		self.platform_adhesion_combo = wx.ComboBox(self.platform_adhesion_panel, -1, '', choices=[_("None"), _("Brim")], style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self.platform_adhesion_combo.SetSelection(int(profile.getPreference('simpleModePlatformAdhesion')))
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(self.platform_adhesion_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP, 10)
		sizer.Add(self.platform_adhesion_combo, 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP, 10)
		self.platform_adhesion_panel.SetSizer(sizer)

		sizer = wx.GridBagSizer()
		sizer.SetEmptyCellSize((0, 0))
		self.SetSizer(sizer)

		sb = wx.StaticBox(printExtruderPanel, label=_("Extruder:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_extruder_options:
			boxsizer.Add(button)
		printExtruderPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printExtruderPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printExtruderPanel, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(printMaterialPanel, label=_("Material:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_material_options:
			boxsizer.Add(button)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (2,0), flag=wx.EXPAND)

		sb = wx.StaticBox(printTypePanel, label=_("Quality:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		for button in self._print_profile_options:
			boxsizer.Add(button)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (0,0), flag=wx.EXPAND)

		sb = wx.StaticBox(self, label=_("Other:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		boxsizer.Add(self.platform_adhesion_panel)
		sizer.Add(boxsizer, (3,0), flag=wx.EXPAND)

		for button in self._print_profile_options:
			button.Bind(wx.EVT_RADIOBUTTON, self._update)
		for button in self._print_material_options:
			button.Bind(wx.EVT_RADIOBUTTON, self._update)
		for button in self._print_extruder_options:
			button.Bind(wx.EVT_RADIOBUTTON, self._update)

		self.printSupport.Bind(wx.EVT_CHECKBOX, self._update)
		self.platform_adhesion_combo.Bind(wx.EVT_COMBOBOX, self._update)

		self._update(None)

	def _update(self, e):
		profile_name = self._getActiveProfileName()
		material_name = self._getActiveMaterialName()
		extruder_name = self._getActiveExtruderName()

		if profile_name is None:
			self._print_profile_options[1].SetValue(True)
			profile_name = self._getActiveProfileName()

		if material_name is None:
			if len(self._print_material_options) > 0:
				self._print_material_options[0].SetValue(True)
				material_name = self._getActiveMaterialName()
			else:
				material_name = ''
		if extruder_name is None:
			if len(self._print_extruder_options) > 0:
				self._print_extruder_options[0].SetValue(True)
				extruder_name = self._getActiveExtruderName()
			else:
				extruder_name = ''

		profile.putPreference('simpleModeProfile', profile_name)
		profile.putPreference('simpleModeMaterial', material_name)
		profile.putPreference('simpleModeExtruder', extruder_name)
		profile.putPreference('simpleModePlatformAdhesion', self.platform_adhesion_combo.GetSelection())

		self._updateAvailableOptions()
		self._callback()

	def _getActiveProfileName(self):
		for button in self._print_profile_options:
			if button.GetValue():
				return button.name
		return None

	def _getActiveMaterialName(self):
		for button in self._print_material_options:
			if button.GetValue():
				return button.name
		return None

	def _getActiveExtruderName(self):
		for button in self._print_extruder_options:
			if button.GetValue():
				return button.name
		return None

	def _updateAvailableOptions(self):
		profile_name = self._getActiveProfileName()
		material_name = self._getActiveMaterialName()
		extruder_name = self._getActiveExtruderName()

		if not self._profile_manager.isValidProfileOption(profile_name, material_name, extruder_name):
			for button in self._print_profile_options:
				if self._profile_manager.isValidProfileOption(button.name, material_name, extruder_name):
					button.SetValue(True)
					profile_name = button.name
		if not self._profile_manager.isValidProfileOption(profile_name, material_name, extruder_name):
			for button in self._print_material_options:
				if self._profile_manager.isValidProfileOption(profile_name, button.name, extruder_name):
					button.SetValue(True)
					material_name = button.name
		if not self._profile_manager.isValidProfileOption(profile_name, material_name, extruder_name):
			for p_button in self._print_profile_options:
				for m_button in self._print_material_options:
					if self._profile_manager.isValidProfileOption(p_button.name, m_button.name, extruder_name):
						m_button.SetValue(True)
						p_button.SetValue(True)
						profile_name = p_button.name
						material_name = m_button.name

		for button in self._print_material_options:
			button.Enable(self._profile_manager.isValidProfileOption(profile_name, button.name, extruder_name))
		for button in self._print_profile_options:
			button.Enable(self._profile_manager.isValidProfileOption(button.name, material_name, extruder_name))

	def getSettingOverrides(self):
		profile_name = self._getActiveProfileName()
		material_name = self._getActiveMaterialName()
		extruder_name = self._getActiveExtruderName()

		settings = {}
		for setting in profile.settingsList:
			if not setting.isProfile():
				continue
			settings[setting.getName()] = setting.getDefault()

		settings.update(self._profile_manager.getSettingsFor(profile_name, material_name, extruder_name))
		if self.printSupport.GetValue():
			settings['support'] = "Exterior Only"
		else:
			settings['support'] = "None"
		if self.platform_adhesion_combo.GetValue() == _("Brim"):
			settings['platform_adhesion'] = "Brim"
		else:
			settings['platform_adhesion'] = "None"
		return settings

	def updateProfileToControls(self):
		pass
