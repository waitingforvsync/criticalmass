# cos[0..255] is an array of round(cos(x)*256) with x scaled from 0..255 to 0..pi/2
# since the first 11 entries will be 256, these won't fit and are truncated to 0
# thus they get special (faster!) handling when the table is accessed.
# 
# from this table we can also get sin(x) = cos[(256-x) & 0xFF]
# note that this actually relies on the value of cos[0] being 0 (truncated from 256)


# atan[0..255] is an array of round(atan(x/256)*128/(pi/4))
# (the result is scaled from 0..pi/2 to 0..255)


# reciplo[1..255] is an array of round(65536/x) & 0xFF 
# reciphi[1..255] is an array of round(65536/x) >> 8
 

# multab[0..510] is an array of (x*x/4)
# mulnegtab[0..510] is an array of ((x-255)*(x-255)/4)


k = math.pi / 512
atan      = [round(math.atan(x/256) / k)        for x in range(0, 256)]
cos       = [round(math.cos(x*k) * 256) & 0xFF  for x in range(0, 256)]
cos_valid = math.ceil(math.acos(255.5/256) / k)

multab    = [x*x // 4              for x in range(0, 512)]
mulnegtab = [(x-255)*(x-255) // 4  for x in range(0, 512)]

reciplo   = [min(round(65536/max(1,x)), 0xFFFF) & 0xFF   for x in range(0, 256)]
reciphi   = [min(round(65536/max(1,x)), 0xFFFF) >> 8     for x in range(0, 256)]



def mul_int_int(a, b):
	return multab[a+b] - mulnegtab[a+(b^0xFF)]
	
def mul_int_frac(a, b):
	return (multab[a+b] - mulnegtab[a+(b^0xFF)] + 128) >> 8

def div_int_frac(a, b):
	return mul_int_int(a, reciphi[b]) + mul_int_frac(a, reciplo[b])


def collision(index0, index1):

	r0 = ball_radius[index0]
	r1 = ball_radius[index1]
	radii = r0 + r1
	
	dx = ball_x[index1] - ball_x[index0]
	dy = ball_y[index1] - ball_y[index0]
	
	absdx = abs(dx)
	absdy = abs(dy)
	
	if absdx >= radii or absdy >= radii:
		return

	if (absdx < absdy):
		ang = atan[div_int_frac(absdx, absdy)]
		if (ang >= cos_valid):
			dist = div_int_frac(absdy, cos[ang])
			overlap = radii - dist
			if (overlap <= 0):
				return
			accy = mul_int_frac(overlap, cos[ang])
		else:
			overlap = radii - absdy
			if (overlap <= 0):
				return
			accy = overlap
		accx = mul_int_frac(overlap, cos[(256-ang) & 0xFF])
	elif (absdx > absdy):
		ang = atan[div_int_frac(absdy, absdx)]
		if (ang >= cos_valid):
			dist = div_int_frac(absdx, cos[ang])
			overlap = radii - dist
			if (overlap <= 0):
				return
			accx = mul_int_frac(overlap, cos[ang])
		else:
			overlap = radii - absdx
			if (overlap <= 0):
				return
			accx = overlap
		accy = mul_int_frac(overlap, cos[(256-ang) & 0xFF])
	else:
		dist = div_int_frac(absdy, cos[128])
		overlap = radii - dist
		if (overlap <= 0):
			return
		accx = accy = mul_int_frac(overlap, cos[128])

	m0 = ball_mass[index0]
	m1 = ball_mass[index1]	
	massfrac0 = div_int_frac(m0, m0 + m1)
	
	acc1x = mul_int_frac(accx, massfrac0)
	acc0x = accx - acc1x
	if dx >= 0:
		ball_accelx[index0] -= acc0x
		ball_accelx[index1] += acc1x
	else:
		ball_accelx[index0] += acc0x
		ball_accelx[index1] -= acc1x

	acc1y = mul_int_frac(accy, massfrac0)
	acc0y = accy - acc1y
	if dy >= 0:
		ball_accely[index0] -= acc0y
		ball_accely[index1] += acc1y
	else:
		ball_accely[index0] += acc0y
		ball_accely[index1] -= acc1y
	
	

