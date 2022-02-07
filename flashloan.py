import smartpy as sp

class Sender(sp.Contract):
    def __init__(self, admin, contract):
        self.init(
            admin = admin,
            contract = contract,
            token_address = sp.address("KT1DddFf7RTvi78YPwsRfemTaMvKWy54GBRc"),
            amount_repay = 0,
            token_id = 0
        )
    
    @sp.entry_point
    def start_flashloan(self, params):
        sp.set_type(params, sp.TRecord(_to = sp.TAddress, amount0Out = sp.TNat, amount1Out = sp.TNat, amount_repay = sp.TNat, token_id = sp.TNat, token_address = sp.TAddress))

        self.data.token_address = params.token_address
        self.data.amount_repay = params.amount_repay
        self.data.token_id = params.token_id

        params_flash = sp.some(
                sp.contract(
                sp.TRecord(
                    amount0Out = sp.TNat,
                    amount1Out = sp.TNat
                ),
                sp.self_address,
                entry_point="execute_operations"
            ).open_some(message = None)
        )

        params_entrypoint = sp.contract(
            sp.TRecord(
                _to = sp.TAddress,
                amount0Out = sp.TNat,
                amount1Out = sp.TNat,
                flash = sp.TOption(
                    sp.TContract(
                        sp.TRecord(
                            amount0Out = sp.TNat,
                            amount1Out = sp.TNat
                        )
                    )
                )
            ),
            self.data.contract,
            entry_point="start_swap"
        ).open_some(message = None)

        params_transfer = sp.record(
            _to = params._to,
            amount0Out = params.amount0Out,
            amount1Out = params.amount1Out,
            flash = params_flash
        )

        sp.transfer(
            params_transfer,
            sp.mutez(0),
            params_entrypoint
        )

    @sp.entry_point
    def execute_operations(self, params):
        sp.set_type(params, sp.TRecord(amount0Out = sp.TNat, amount1Out = sp.TNat))
        
        """
        Opérations avant remboursement a éxécuter ici
        """
        
        transfer_params = sp.list([
            sp.record(
                from_ = sp.self_address,
                txs = sp.list([
                sp.record(
                        amount = self.data.amount_repay,
                        to_ = self.data.contract,
                        token_id = self.data.token_id
                    )
                ])
            )
        ])

        sp.transfer(
            transfer_params,
            sp.mutez(0),
            sp.contract(
                sp.TList(
                    sp.TRecord(
                        from_ = sp.TAddress,
                        txs = sp.TList(
                            sp.TRecord(
                                amount = sp.TNat,
                                to_ = sp.TAddress,
                                token_id = sp.TNat
                            ).layout(("to_", ("token_id", "amount")))
                        )
                    ).layout(("from_", "txs"))
                ),
                self.data.token_address,
                entry_point="transfer"
            ).open_some(message = None)
        )

    @sp.entry_point
    def set_admin(self, admin):
        sp.set_type(admin, sp.TAddress)

        self.data.admin = admin

    @sp.entry_point
    def set_contract(self, contract):
        sp.set_type(contract, sp.TAddress)
        
        self.data.contract = contract

sp.add_compilation_target(
    "contract",
    Sender(
        admin = sp.address("ADMIN_ADDRESS"),
        contract = sp.address("LP_POOL")
    )
)

