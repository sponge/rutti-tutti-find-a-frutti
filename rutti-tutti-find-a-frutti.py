from omg import *
from omg import txdef
import itertools
import argparse
import sys

# returns True if the two rectangles in the form of [x1, y1, x2, y2] intersect
def doesRectangleOverlap(rec1, rec2):
    def intersect(p_left, p_right, q_left, q_right):
        return min(p_right, q_right) > max(p_left, q_left)
    return (intersect(rec1[0], rec1[2], rec2[0], rec2[2]) and  # width > 0
            intersect(rec1[1], rec1[3], rec2[1], rec2[3]))    # height > 0


# returns True if a texture lump's patch list has intersecting patches
def doTexturesIntercept(patches, lump):
    for p1, p2 in itertools.combinations(lump.patches, 2):
        b1 = patches[p1.name]
        b2 = patches[p2.name]

        rect1 = [p1.x, p1.y, p1.x + b1.width, p1.y + b1.height]
        rect2 = [p2.x, p2.y, p2.x + b2.width, p2.y + b2.height]

        if doesRectangleOverlap(rect1, rect2):
            return True

    return False


parser = argparse.ArgumentParser(
    description='Scan DOOM engine maps, scanning for possible medusa effects, and tutti-frutti errors.')
parser.add_argument(
    '--iwad', help='filesystem path to the IWAD to use for resources')
parser.add_argument(
    '--pwad', help='filesystem path to the PWAD to use for resources, and level scanning')
args = parser.parse_args()

iwad = WAD(args.iwad)
pwad = WAD(args.pwad)

#iwad = WAD("c:/chocodoom/doom.wad")
#pwad = WAD("c:/chocodoom/neis.wad")

if len(iwad.maps) == 0 or len(pwad.maps) == 0:
    parser.print_help()
    sys.exit(1)

# combine the texture definitions into one dict
textures = dict(txdef.Textures(iwad.txdefs))
textures.update(dict(txdef.Textures(pwad.txdefs)))

# combine the iwad and pwad patches into a single dict
patches = dict(iwad.patches)
patches.update(dict(pwad.patches))

# create a list of textures that are potentially problematic
overlapping_textures = {k: lump for (k, lump) in textures.items() if len(
    lump.patches) > 1 and doTexturesIntercept(patches, lump)}

# loop through each map and scan for errors
for map_name, lump in pwad.maps.items():
    dmap = MapEditor(lump)
    warnings = []

    # detect potential medusas
    # potential because we don't check to see if an overlapping column is actually rendered
    for k, line in enumerate(dmap.linedefs):
        # 1 sided linedefs can't be medusa
        if line.two_sided == False:
            continue

        front_tx_mid = dmap.sidedefs[line.front].tx_mid
        back_tx_mid = dmap.sidedefs[line.back].tx_mid
        for tx in [front_tx_mid, back_tx_mid]:
            if tx in overlapping_textures:
                v1 = dmap.vertexes[line.vx_a]
                v2 = dmap.vertexes[line.vx_b]
                warnings.append(
                    f'possible medusa at line #{k}: midtex is {front_tx_mid}')
                break

    for k, line in enumerate(dmap.linedefs):
        # if all the textures on the front and back are 128 height, we definitely do not have tutti
        line_textures = []
        front_side = dmap.sidedefs[line.front]
        back_side = dmap.sidedefs[line.back] if line.two_sided else None

        # grab all the textures used for this linedef
        if line.two_sided:
            line_textures.extend(
                [front_side.tx_low, front_side.tx_mid, front_side.tx_up])
            line_textures.extend(
                [back_side.tx_low, back_side.tx_mid, back_side.tx_up])
        else:
            # 1 sided line, we only care about midtex
            line_textures.append(front_side.tx_mid)

        # lookup textures, filtering out empty textures which have a - as their name
        line_textures = [textures[x] for x in line_textures if x != '-']

        if (all(x.height == 128 for x in line_textures)):
            # all textures have 128 height, no tutti is possible
            continue

        if not line.two_sided:
            # if it's a 1 sided line, and the texture would loop, it will be tutti
            sector = dmap.sectors[front_side.sector]
            tex_height = textures[front_side.tx_mid].height
            sector_height = sector.z_ceil - sector.z_floor

            # if the texture is going to loop in the visible area, we likely have a problem
            if sector_height - abs(front_side.off_y) > tex_height:
                warnings.append(
                    f'likely tutti at line #{k}: 1s sector height is {sector_height} and offset is {front_side.off_y} but texture {front_side.tx_mid} height is {tex_height}')
                break
        else:
            sides = [('front', front_side, back_side),
                     ('back', back_side, front_side)]

            # for the front and back sides, grab the sector and texture information
            for side_str, side, other_side in sides:
                sector = dmap.sectors[side.sector]
                other_sector = dmap.sectors[other_side.sector]
                low_tex = textures[side.tx_low] if side.tx_low != '-' else None
                up_tex = textures[side.tx_up] if side.tx_up != '-' else None

                # if there's a lower texture set and the texture height isn't 128, we potentially have an issue
                if low_tex is not None and low_tex.height != 128:
                    # calculate the height of the floor part of the wall
                    lower_wall_height = sector.z_floor - other_sector.z_floor
                    
                    # ignore this one if we're on the wrong side
                    if lower_wall_height < 0:
                        continue

                    # if the texture is going to loop, it is possibly an issue
                    if lower_wall_height - abs(side.off_y) > low_tex.height:
                        warnings.append(
                            f'possible tutti at line #{k}: {side_str} side has a lower texture {side.tx_low} with a height of {low_tex.height}, y offset of {side.off_y}, and lower wall height of {lower_wall_height}')

                # same thing as above, but comparing sector ceilings to determine ceiling wall size
                if up_tex is not None and up_tex.height != 128:
                    upper_wall_height = sector.z_ceil - other_sector.z_ceil
                    if upper_wall_height < 0:
                        continue

                    if upper_wall_height > abs(side.off_y) > up_tex.height:
                        warnings.append(
                            f'possible tutti at line #{k}: {side_str} side has a lower texture {side.tx_up} with a height of {up_tex.height}, y offset of {side.off_y}, and upper wall height of {upper_wall_height}')

    # if we have any warnings from this map, print them now
    if len(warnings):
        print(f'{map_name}:')
        for warning in warnings:
            print(f'    - {warning}')
        print('')

        continue
