from ... import path

import numpy as np
import pandas as pd
import datetime

years = range(2005, 2014+1)

def update_date(df):
    for i, r in df.iterrows():
        for k, v in df.iteritems():
            try:
                r[k] = datetime.datetime.strptime('%d-%s' % (i, v[i]), '%Y-%m/%d')
            except:
                r[k] = np.nan
    return df

########
# Fuji #
########
def load_fuji():
    fuji_bt = ['4/26', '4/24', '4/24', '4/20', '4/14', '4/14', '4/28', '4/25', '4/27', '4/18']
    fuji_fb = ['4/26', '4/28', '4/27', '4/23', '4/20', '4/20', '5/1', '4/28', '4/28', '4/22']
    fuji_hm = ['10/26', '10/30', '10/27', '10/30', '10/26', '10/26', '10/31', '10/29', '10/29', np.nan]
    fuji = pd.DataFrame(data={
        'Blooming time': fuji_bt,
        'Full bloom stage': fuji_fb,
        'Harvest maturity': fuji_hm,
    }, index=years)
    update_date(fuji)
    #fuji.to_pickle('fuji.pkl')
    return fuji

###########
# Tsugaru #
###########

def load_tsugaru():
    tsugaru = pd.DataFrame(data={
        'Blooming time': ['4/23', '4/24', '4/24', '4/20', '4/15', '4/15', '4/26', '4/24', '4/24', '4/16'],
        'Full bloom stage': ['4/25', '4/27', '4/26', '4/23', '4/20', '4/20', '4/29', '4/28', '4/25', '4/20'],
        'Harvest maturity': ['8/30', '8/16', '8/20', '8/18', '8/23', '8/23', '8/23', '8/16', '8/19', '8/15'],
    }, index=years)
    update_date(tsugaru)
    #tsugaru.to_pickle('tsugaru.pkl')
    return tsugaru

##########
# Hongro #
##########

def load_hongro():
    hongro = pd.DataFrame(data={
        'Blooming time': ['4/20', '4/22', '4/19', '4/18', '4/12', '4/12', '4/25', '4/23', '4/22', '4/13'],
        'Full bloom stage': ['4/23', '4/25', '4/23', '4/21', '4/17', '4/17', '4/28', '4/27', '4/24', '4/17'],
        'Harvest maturity': ['9/05', '8/28', '8/27', '9/04', '9/10', '9/10', '9/10', '8/29', '9/05', '8/27'],
    }, index=years)
    update_date(hongro)
    #hongro.to_pickle('hongro.pkl')
    return hongro

########################
# Combined Observation #
########################

def conv():
    fuji = load_fuji()
    tsugaru = load_tsugaru()
    hongro = load_hongro()
    apple = pd.concat([fuji, tsugaru, hongro], keys=['Fuji', 'Tsugaru', 'Hongro'], names=['cultivar', 'year'])

    apple['station'] = 823
    apple.set_index('station', append=True, inplace=True)
    apple = apple.reorder_levels(['station', 'cultivar', 'year'])

    outname = path.input.outfilename('pkl/obs', 'apple_gunwi', 'pkl')
    apple.to_pickle(outname)
