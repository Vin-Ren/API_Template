import re


dict_updater = lambda base,updater:(lambda dbase,dupdt:[dbase.update(dupdt), dbase][-1])(base.copy(), updater)

remove_illegal_name_characters = lambda name: re.sub(r"[/\\:*?<>|\"]", '', name)
remove_illegal_name_characters_except_slashes = lambda name: re.sub(r"[:*?<>|\"]", '', name)
