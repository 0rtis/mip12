from typing import List
import sys
import logging
import secrets


from poc_implementation.mip12.mochimo_application_machine import MAM, Chat
from poc_implementation.mip12.mochimo_application_machine import APP_TEMPLATE_TYPE_ASSETS, APP_TEMPLATE_TYPE_AMM, APP_TEMPLATE_TYPE_MARKETPLACE, APP_TEMPLATE_TYPE_CHAT
from poc_implementation.mip12.mochimo_application_machine import MCM, Assets
from poc_implementation.mip12.mochimo_application_machine import MCM_APP_ID, APP_INSTANCE_ID_LENGTH,  INT_ENCODING, STR_ENCODING, DATA_LENGTH
from poc_implementation.mip12.application import ApplicationTemplate


def payload_send_msg(sender, msg_destination, msg_content):
    logger.info("Sending msg with address {}".format(account_address_1_str))
    msg_dst = "@world".encode(STR_ENCODING)
    msg_content = "Hello !".encode(STR_ENCODING)
    payload = len(msg_dst).to_bytes(2, INT_ENCODING) + msg_dst + len(msg_content).to_bytes(2, INT_ENCODING) + msg_content


def payload_create_address(new_address: bytes, amount: int):
    return new_address + amount.to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)


def payload_create_token(token: bytes, admin: bytes):
    token_data = MAM.pack_int(0) + MAM.pack_int(18)
    return token + int(Assets.TYPE_FUNGIBLE).to_bytes(1, INT_ENCODING) + admin + MAM.array_to_bytes([]) + len(token_data).to_bytes(DATA_LENGTH, INT_ENCODING) + token_data


def payload_mint_token(token: bytes, amount: int, destination: bytes):
    return token + MAM.array_to_bytes([MAM.pack_int(amount) + destination])


def payload_transfer_token(token: bytes, amount: int, destination: bytes):
    return MAM.array_to_bytes([token + MAM.pack_int(amount) + destination])


def payload_create_pool(token_a: bytes, amount_a: int, token_b: bytes, amount_b: int, fee_bps: int):
    return token_a + MAM.pack_int(amount_a) + token_b + MAM.pack_int(amount_b) + fee_bps.to_bytes(2, INT_ENCODING) + assets_app_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING)


def payload_swap(a_to_b: bool, amount_in: int, min_amount_out: int):
    return int(1 if a_to_b else 0).to_bytes(1, INT_ENCODING) + MAM.pack_int(amount_in) + MAM.pack_int(min_amount_out)


def payload_create_marketplace():
    return MAM.pack_int(0) + MAM.pack_int(0) + assets_app_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING)


def payload_list_marketplace(goods_token: bytes, good_amount: int, price_token: bytes, price_amount: int,):
    goods = MAM.array_to_bytes([goods_token + MAM.pack_int(good_amount)])
    prices = MAM.array_to_bytes([price_token + MAM.pack_int(price_amount)])
    return len(goods).to_bytes(DATA_LENGTH, INT_ENCODING) + goods + len(prices).to_bytes(DATA_LENGTH, INT_ENCODING) + prices


def payload_match_marketplace(offer_address: bytes, offer_id: int):
    return offer_address + MAM.pack_int(offer_id)


def payload_send_msg(recipient: bytes, msg: bytes):
    return len(recipient).to_bytes(DATA_LENGTH, INT_ENCODING) + recipient + len(msg).to_bytes(DATA_LENGTH, INT_ENCODING) + msg


def execute(caller, app_id, function_selector, function_param):
    expected_gas_used, expected_gas_cost, expected_error = mam.call(True, caller, None, app_id, function_selector, function_param)
    if expected_error is not None:
        raise Exception("Error on dry run:\t{}".format(expected_error))
    logger.info("Expected gas:\t{} / {} nMCM".format(expected_gas_used, expected_gas_cost))
    gas_used, gas_cost, error = mam.call(False, caller, expected_gas_used, app_id, function_selector, function_param)
    if expected_error is not None:
        raise Exception("Error on dry run:\t{}".format(expected_error))
    logger.info("Gas used:\t{} / {} nMCM".format(expected_gas_used, expected_gas_cost))
    assert expected_gas_used == gas_used


def get_address_info_log(address: bytes, mam: MAM, tokens: List[str]=[]):
    log = '----{}----'.format(address.hex())
    account_storage = mam.account_storage.read(address)
    if len(account_storage) <= 0:
        log = '{}\n\tADDRESS DOES NOT EXISTS'.format(log)
        return log
    account_array = MAM.parse_array(account_storage)

    account_mcm_storage, account_mcm_index = MAM.get_app_data_from_array(MCM_APP_ID, account_array)
    mcm_balance = MCM.get_balance(account_mcm_storage)
    log = '{}\n\tMCM:\t{}'.format(log, mcm_balance)

    account_assets_storage, account_assets_index = MAM.get_app_data_from_array(assets_app_id, account_array)
    account_tokens = {} if account_assets_index < 0 else Assets.get_account_tokens(account_assets_storage)
    for token in tokens:
        log = '{}\n\t{}:\t{}'.format(log, token, account_tokens[token] if token in account_tokens else 0)

    account_chat_storage, account_chat_index = MAM.get_app_data_from_array(chat_app_id, account_array)
    if account_chat_index < 0:
        log = '{}\n\tChat: *NO MESSAGE*'.format(log)
    else:
        log = '{}\n\tChat: {}'.format(log, Chat.decode_entry(account_chat_storage[APP_INSTANCE_ID_LENGTH:]))

    return log


if __name__ == "__main__":

    log_format = '%(asctime)s|%(name)s|%(filename)s:%(lineno)d|%(levelname)s: %(message)s'
    logger = logging.getLogger("MIP12")
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)

    mam = MAM()

    assets_template = ApplicationTemplate(_type=APP_TEMPLATE_TYPE_ASSETS)
    mam.add_app_template(assets_template)
    assets_app_id = mam.create_instance(assets_template.type)

    amm_template = ApplicationTemplate(_type=APP_TEMPLATE_TYPE_AMM)
    mam.add_app_template(amm_template)
    amm_app_id = mam.create_instance(amm_template.type)

    mp_template = ApplicationTemplate(_type=APP_TEMPLATE_TYPE_MARKETPLACE)
    mam.add_app_template(mp_template)
    mp_app_id = mam.create_instance(mp_template.type)

    chat_template = ApplicationTemplate(_type=APP_TEMPLATE_TYPE_CHAT)
    mam.add_app_template(chat_template)
    chat_app_id = mam.create_instance(chat_template.type)

    account_address_1 = bytes.fromhex('111111111111111111111111')
    account_address_1_str = account_address_1.hex()
    account_address_2 = bytes.fromhex('222222222222222222222222')
    account_address_2_str = account_address_2.hex()

    lama_token = 'LAMA'.encode(STR_ENCODING)
    fiat_token = 'FIAT'.encode(STR_ENCODING)
    tokens = [lama_token.decode(STR_ENCODING), fiat_token.decode(STR_ENCODING)]

    mam.account_storage.write(account_address_1, 
                              MAM.account_array_to_bytes([
                                                            MCM_APP_ID.to_bytes(DATA_LENGTH, INT_ENCODING) + int(1_000_000).to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)
                              ]))

    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    logger.info("Creating new account {} with {} MCM".format(account_address_2_str, 500_000))
    create_address_payload = payload_create_address(account_address_2, 500_000)
    execute(account_address_1, MCM_APP_ID, 1, create_address_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Creating token {} with account {}".format(lama_token.decode(STR_ENCODING), account_address_1_str))
    create_token_payload = payload_create_token(lama_token, account_address_1)
    execute(account_address_1, assets_app_id, 1, create_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Minting 1337000 {} token to account {}".format(lama_token.decode(STR_ENCODING), account_address_2_str))
    mint_token_payload = payload_mint_token(lama_token, 1337_000, account_address_2)
    execute(account_address_1, assets_app_id, 2, mint_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Transferring 777_000 {} token from {} to {}".format(lama_token.decode(STR_ENCODING), account_address_2_str, account_address_1_str))
    transfer_token_payload = payload_transfer_token(lama_token, 777_000, account_address_1)
    execute(account_address_2, APP_TEMPLATE_TYPE_ASSETS, 3, transfer_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Creating token {} with account {}".format(fiat_token.decode(STR_ENCODING), account_address_1_str))
    create_token_payload = payload_create_token(fiat_token, account_address_1)
    execute(account_address_1, assets_app_id, 1, create_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Minting 102400 {} token to account {}".format(fiat_token.decode(STR_ENCODING), account_address_2_str))
    mint_token_payload = payload_mint_token(fiat_token, 1024_00, account_address_2)
    execute(account_address_1, assets_app_id, 2, mint_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Transferring 51200 {} token from {} to {}".format(fiat_token.decode(STR_ENCODING), account_address_2_str, account_address_1_str))
    transfer_token_payload = payload_transfer_token(fiat_token, 512_00, account_address_1)
    execute(account_address_2, assets_app_id, 3, transfer_token_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Creating {} {}/{} {} AMM pool with account {}".format(100_000, lama_token.decode(STR_ENCODING), 100_00, fiat_token.decode(STR_ENCODING), account_address_1_str))
    create_pool_payload = payload_create_pool(lama_token, 100_000, fiat_token, 100_00, 30)
    execute(account_address_1, amm_app_id, 1, create_pool_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Swapping 1000 {} for 9000 {} (minimum) with account {}".format(fiat_token.decode(STR_ENCODING), lama_token.decode(STR_ENCODING), account_address_2_str))
    swap_payload = payload_swap(False, 10_00, 9000)
    execute(account_address_2, amm_app_id, 5, swap_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Creating marketplace with account {}".format(account_address_1_str))
    create_marketplace_payload = payload_create_marketplace()
    execute(account_address_1, mp_app_id, 1, create_marketplace_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Listing offer 1 {} for 1 {} on marketplace with account {}".format(lama_token.decode(STR_ENCODING), fiat_token.decode(STR_ENCODING), account_address_2_str))
    list_marketplace_payload = payload_list_marketplace(lama_token, 1, fiat_token, 1)
    execute(account_address_2, mp_app_id, 2, list_marketplace_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Matching offer on marketplace with account {}".format(account_address_1_str))
    payload_match_marketplace_payload = payload_match_marketplace(account_address_2, 0)
    execute(account_address_1, mp_app_id, 3, payload_match_marketplace_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()

    logger.info("Sending msg 'Hello' to 'world' with account {}".format(account_address_2_str))
    send_msg_payload = payload_send_msg('world'.encode(STR_ENCODING), 'Hello !'.encode(STR_ENCODING))
    execute(account_address_2, chat_app_id, 1, send_msg_payload)
    logger.info('\n{}'.format(get_address_info_log(account_address_1, mam, tokens)))
    logger.info('\n{}'.format(get_address_info_log(account_address_2, mam, tokens)))

    mam.blockchain.mine_block()


