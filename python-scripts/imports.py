
# external libraries
import os
import re
import httpx
import random
import logging
import asyncio
import discord
import traceback

from discord.ext.tasks import loop


# internal scripts - order of import matters; load the scripts in order of lowest to highest dependency
import var_global
from var_global import *

import var_secret
from var_secret import *

from func_utils import *
from func_http import *

from bot_logging import *
from bot_messaging import *

from bot_actions import *
