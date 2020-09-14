# Made by red-green (https://github.com/red-green/)
# Copied with permission from https://github.com/red-green/CorpBot.py/blob/patch-1/Cogs/JazUtils.py

import asyncio
import discord
import random
import datetime
import colorsys
from   discord.ext import commands

# constant for paginating embeds
EMBED_MAX_LEN = 2048
MAX_USERS = 30 # max people to list for !whohas
STATUSMAP1 = {discord.Status.online:'1',discord.Status.dnd:'2',discord.Status.idle:'3'} ##for sorting
STATUSMAP2 = {discord.Status.online:':green_circle:',discord.Status.dnd:':no_entry_sign:',discord.Status.idle:':crescent_moon:',discord.Status.offline:':black_circle:'}

class JazUtils(commands.Cog):
	"""Various useful commands related to checking users and roles."""
	# Init with the bot reference, and a reference to the settings var
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def snowflake(self, ctx, *, sid : str = None):
		"""Show the date a snowflake ID was created"""

		sid = int(sid)
		timestamp = ((sid >> 22) + 1420070400000) / 1000 # python uses seconds not milliseconds
		cdate = datetime.datetime.utcfromtimestamp(timestamp)
		msg = "Snowflake created {}".format(cdate.strftime('%A, %B %d %Y at %H:%M:%S UTC'))
		await ctx.channel.send(msg)
		return

	@commands.command(pass_context=True)
	async def fullsnowflake(self, ctx, *, sid : str = None):
		"""Show all available data about a snowflake ID"""
		c = False
		sid = int(sid)
		timestamp = ((sid >> 22) + 1420070400000) / 1000 # python uses seconds not milliseconds
		iwid = (sid & 0x3E0000) >> 17
		ipid = (sid & 0x1F000) >> 12
		icount = sid & 0xFFF

		cdate = datetime.datetime.utcfromtimestamp(timestamp)
		fdate = cdate.strftime('%A, %B %d %Y at %H:%M:%S UTC')

		embed = discord.Embed(title=sid, description='Discord snowflake ID')
		embed.add_field(name="Date created", value=fdate)
		embed.add_field(name="Internal worker/process", value="{}/{}".format(iwid,ipid))
		embed.add_field(name="Internal counter", value=icount)
		if self.bot.get_user(sid) != None:
			c = True
			embed.add_field(name="As user tag", value=self.bot.get_user(sid).mention)
		if self.bot.get_channel(sid) != None:
			c = True
			b = self.bot.get_channel(sid)
			embed.add_field(name="As channel tag", value=b.mention)
			if b.category != None:
				embed.add_field(name="In category:", value=b.category)
		if self.bot.get_guild(sid) != None:
			c = True
			embed.add_field(name="As guild name", value=self.bot.get_guild(sid).name)
		if self.bot.get_emoji(sid) != None:
			c = True
			b = self.bot.get_emoji(sid)
			embed.add_field(name="As emoji", value="{} [Link]({})".format(b, b.url))
		if ctx.message.guild.get_role(sid) != None:
			c = True
			embed.add_field(name="As role tag", value=ctx.message.guild.get_role(sid).mention)
		if c == False:
			embed.add_field(name= "Failed to find snowflake", value="Missing permissions, or snowflake doesn't exist.")
		await ctx.channel.send(embed=embed)


	## role listing and queries

	def role_check(self, user, role_query):
		# returns True or False if a user has named role
		for role in user.roles:
			if role.name in role_query:
				return True
		return False

	def alphanum_filter(self, text):
		# filter for searching a role by name without having to worry about case or punctuation
		return ''.join(i for i in text if i.isalnum()).lower()

	def rolelist_filter(self, roles, id_list):
		# filters the full role hierarchy based on the predefined lists above
		out_roles = []
		for role in roles:
			if int(role.id) in id_list:
				out_roles.append(role)
		return out_roles

	def get_named_role(self, server, rolename):
		# finds a role in a server by name
		check_name = self.alphanum_filter(rolename)
		for role in server.roles:
			if self.alphanum_filter(role.name) == check_name:
				return role
		return None

	def role_accumulate(self, check_roles, members):
		## iterate over the members to accumulate a count of each role
		rolecounts = {}
		for role in check_roles: # populate the accumulator dict
			if not role.is_default():
				rolecounts[role] = 0

		for member in members:
			for role in member.roles:
				if role in check_roles and not role.is_default(): # want to exclude @everyone from this list
					rolecounts[role] += 1

		return rolecounts

	async def rolelist_paginate(self, ctx, rlist, title='Role List'):
		# takes a list of roles and counts and sends it out as multiple embed as nessecary
		pages = []
		buildstr = ''
		for role,count in rlist: # this generates and paginates the info
			line = '{} {}\n'.format(count,role.mention)
			if len(buildstr) + len(line) > EMBED_MAX_LEN:
				pages.append(buildstr) # split the page here
				buildstr = line
			else:
				buildstr += line
		if buildstr:
			pages.append(buildstr) #if the string has data not already listed in the pages, add it

		for index,page in enumerate(pages): # enumerate so we can add a page number
			embed = discord.Embed(title='{} page {}/{}'.format(title, index+1, len(pages)), description=page)
			await ctx.channel.send(embed=embed)

	@commands.command(pass_context=True)
	async def roles(self, ctx, sort_order:str='name'):
		"""Shows roles and their member counts. Takes one argument,
		sort_order, which can be default, name, count, or rainbow."""

		if not sort_order in ['default', 'name', 'count', 'rainbow']: # make sure it has valid args
			await ctx.channel.send("Invalid arguments. Check the help for this command.")
			return
		
		check_roles = ctx.message.guild.roles # we use roles for these because sometimes we want to see the order
		
		## now we iterate over the members to accumulate a count of each role
		rolecounts = self.role_accumulate(check_roles, ctx.message.guild.members)
		
		sorted_list = []
		if sort_order == 'default': # default sort = the server role hierarchy
			for role in check_roles:
				if role in rolecounts:
					sorted_list.append((role, rolecounts.get(role,0)))
		elif sort_order == 'name': # name sort = alphabetical by role name
			sorted_list = sorted(rolecounts.items(), key=lambda tup: tup[0].name.lower())
		elif sort_order == 'count': # count sort = decreasing member count
			sorted_list = sorted(rolecounts.items(), key=lambda tup: tup[1], reverse=True)
		elif sort_order == 'rainbow': # color sort: by increasing hue value in HSV color space
			sorted_list = sorted(rolecounts.items(), key=lambda tup: colorsys.rgb_to_hsv(tup[0].color.r, tup[0].color.g, tup[0].color.b)[0])
		
		if not sorted_list: # another failsafe
			return

		await self.rolelist_paginate(ctx,sorted_list) # send the list to get actually printed to discord

	@commands.command(pass_context=True)
	async def rolecall(self, ctx, *, rolename):
		"""Counts the number of members with a specific role."""
		check_role = self.get_named_role(ctx.message.guild, rolename)
		if not check_role:
			await ctx.channel.send("I can't find that role!")
			return

		count = 0
		online = 0
		for member in ctx.message.guild.members:
			if check_role in member.roles:
				count += 1
				if member.status != discord.Status.offline:
					online += 1

		embed = discord.Embed(title=check_role.name, description='{}/{} online'.format(online, count), color=check_role.color)
		embed.set_footer(text='ID: {}'.format(check_role.id))
		await ctx.channel.send(embed=embed)

	@commands.command(pass_context=True)
	async def whohas(self, ctx, *, rolename):
		"""Lists the people who have the specified role alongside their online status.
		Can take a -nick or -username argument to enhance output."""
		mode = 0 # tells how to display: 0 = just mention, 1 = add nickname, 2 = add username
		if '-nick' in rolename:
			mode = 1
			rolename = rolename.replace('-nick','')
		elif '-username' in rolename:
			mode = 2
			rolename = rolename.replace('-username','')

		check_role = self.get_named_role(ctx.message.guild, rolename)
		if not check_role:
			await ctx.channel.send("I can't find that role!")
			return

		users = []
		for member in ctx.message.guild.members:
			if check_role in member.roles:
				users.append(member)

		sorted_list = sorted(users, key=lambda usr: (STATUSMAP1.get(usr.status,'4')) + (usr.nick.lower() if usr.nick else usr.name.lower()))
		truncated = False
		if len(sorted_list) > MAX_USERS:
			sorted_list = sorted_list[:MAX_USERS] ## truncate to the limit
			truncated = True
		if mode == 2: # add full username
			page = '\n'.join('{} {} ({}#{})'.format(STATUSMAP2.get(member.status, ':black_circle:'), member.mention, member.name, member.discriminator) for member in sorted_list) # not bothering with multiple pages cause 30 members is way shorter than one embed
		elif mode == 1: # add nickname
			page = '\n'.join('{} {} ({})'.format(STATUSMAP2.get(member.status, ':black_circle:'), member.mention, member.display_name) for member in sorted_list)
		else:
			page = '\n'.join('{} {}'.format(STATUSMAP2.get(member.status, ':black_circle:'), member.mention) for member in sorted_list)

		if truncated:
			page += '\n*and {} more...*'.format(len(users) - MAX_USERS)

		embed = discord.Embed(title='{} members with {}'.format(len(users), check_role.name), description=page, color=check_role.color)
		embed.set_footer(text='ID: {}'.format(check_role.id))
		await ctx.channel.send(embed=embed)

	@commands.command(pass_context=True)
	async def rolecount(self, ctx):
		"""Simply counts the number of roles on the server. (excluding @everyone)"""
		await ctx.channel.send('This server has {} total roles.'.format(len(ctx.message.guild.roles) - 1))

	@commands.command(pass_context=True)
	async def emptyroles(self, ctx):
		"""Shows a list of roles that have zero members."""

		check_roles = ctx.message.guild.roles # grab in hierarchy order so they're easier to find in the server settings
		rolecounts = self.role_accumulate(check_roles, ctx.message.guild.members) # same accumulate as the `roles` command

		sorted_list = []
		for role in check_roles:
			if role in rolecounts and rolecounts[role] == 0: # only add if count = 0
				sorted_list.append((role, rolecounts.get(role,0)))

		if not sorted_list: # another failsafe
			await ctx.channel.send('Seems there are no empty roles...')

		await self.rolelist_paginate(ctx, sorted_list, title='Empty Roles')

def setup(bot):
	# Add the bot
	bot.add_cog(JazUtils(bot))