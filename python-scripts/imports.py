
# external libraries
import io
import os
import re
import sys
import json
import random
import logging
import asyncio
import datetime
import subprocess

from pathlib import Path
from httpx import AsyncClient
from traceback import format_exception

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.tasks import loop


# internal scripts - order of import matters; load the scripts in order of lowest to highest dependency
import var_global
from var_global import *

import var_secret
from var_secret import *

from func_utils import *
from func_http import *
from func_git import *

from bot_logging import *
from bot_handlers import *
from bot_sync import *
