# coding=utf-8
import os
import logging
import re

def load_pay_imgs(imgs_dir):
    load_pay_imgs = []
    if not os.path.isdir(imgs_dir):
        logging.err('load_pay_imgs images fail, imgs_dir not a dir:%s', imgs_dir)
        return load_pay_imgs

    imgs = os.listdir(imgs_dir) 
    #过滤掉不合规则的
    for img in imgs:
        prefix = re.search('(\d+).png', img, re.DOTALL)
        if not prefix or len(prefix.group(1))!=8:
            continue
        load_pay_imgs.append(prefix.group(1))
    return load_pay_imgs

def crt_paytitle(male, child, ly_type, room):
    ly_title = {1:'一日游', 2:'两日游'}
    
    if room == 0:
        pay_title = '%d成人%d小孩， %s，无房'%(male, child, ly_title[ly_type])
    else:
        pay_title = '%d成人%d小孩， %s，%2d房'%(male, child, ly_title[ly_type], room)

    return pay_title

def cal_payment(male, child, ly_type, room):
    if ly_type == 1:
        payment = male*108 + child*55 + room*100
    elif ly_type == 2:
        payment = male*188 + child*95 + room*100
    else:
        logging.err('cal_payment fail, invalid ly_type:%s', ly_type)
    return payment

if __name__=='__main__':
    '''
    imgs = load_pay_imgs('./static/imgs_pay')
    print(imgs)

    '''
    male, child, ly_type, room = 2, 3, 2, 2
    pay_title = crt_paytitle(male, child, ly_type, room)
    print(pay_title)
    payment = cal_payment(male, child, ly_type, room)
    print(payment)
    

