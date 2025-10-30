# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon
import odoo.tests

from odoo import fields, Command
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestGeneralLedgerReport(TestAccountReportsCommon, odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Give codes in company_1 to the accounts in company_2.
        context = {'allowed_company_ids': [cls.company_data['company'].id, cls.company_data_2['company'].id]}
        cls.company_data_2['default_account_payable'].with_context(context).code = '211010'
        cls.company_data_2['default_account_revenue'].with_context(context).code = '400010'
        cls.company_data_2['default_account_expense'].with_context(context).code = '600010'
        cls.env['account.account'].search([
            ('company_ids', '=', cls.company_data_2['company'].id),
            ('account_type', '=', 'equity_unaffected')
        ]).with_context(context).code = '999989'

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_2',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_expense'].id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2017_2.action_post()

        # Archive 'default_journal_bank' to ensure archived entries are not filtered out.
        cls.company_data_2['default_journal_bank'].active = False

        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False

    @property
    def report(self):
        return self.env.ref('account_reports.general_ledger_report')

    # -------------------------------------------------------------------------
    # TESTS: General Ledger
    # -------------------------------------------------------------------------
    def test_general_ledger_unaffected_earnings_current_fiscal_year(self):
        def invoice_move(date):
            return self.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string(date),
                'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            })

        move_2009_12 = invoice_move('2009-12-31')
        move_2009_12.action_post()

        move_2010_01 = invoice_move('2010-01-31')
        move_2010_01.action_post()

        move_2010_02 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2010-02-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,    'credit': 300.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2010_02.action_post()

        move_2010_03 = invoice_move('2010-03-01')
        move_2010_03.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2010-02-01'), fields.Date.from_string('2010-02-28'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('211000 Account Payable',              2100.0,         0.0,            2100.0),
                ('400000 Product Sales',                0.0,            3300.0,         -3300.0),
                ('600000 Expenses',                     2200.0,         0.0,            2200.0),
                ('999999 Undistributed Profits/Losses', 2000.0,         3000.0,         -1000.0),
                ('Total General Ledger',                6300.0,         6300.0,         0.0),
            ],
            options,
        )

    def test_general_ledger_unaffected_earnings_previous_fiscal_year(self):
        def invoice_move(date):
            return self.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string(date),
                'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            })

        move_2009_12 = invoice_move('2009-12-31')
        move_2009_12.action_post()

        move_2010_01 = invoice_move('2010-01-31')
        move_2010_01.action_post()

        move_2010_02 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2010-02-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,    'name': 'payable', 'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0, 'credit': 0.0,    'name': 'expense', 'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,    'credit': 300.0, 'name': 'revenue', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2010_02.action_post()

        move_2010_03 = invoice_move('2010-03-01')
        move_2010_03.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2010-01-01'), fields.Date.from_string('2010-02-28'))
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('211000 Account Payable',              2100.0,         0.0,             2100.0),
                ('400000 Product Sales',                0.0,            3300.0,         -3300.0),
                ('600000 Expenses',                     2200.0,         0.0,             2200.0),
                ('999999 Undistributed Profits/Losses', 2000.0,         3000.0,         -1000.0),
                ('Total General Ledger',                6300.0,         6300.0,         0.0),
            ],
            options,
        )

    def test_general_ledger_fold_unfold_multicompany_multicurrency(self):
        ''' Test unfolding a line when rendering the whole report. '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('121000 Account Receivable',           1000.0,         0.0,            1000.0),
                ('211000 Account Payable',              100.0,          0.0,            100.0),
                ('211010 Account Payable',              50.0,           0.0,            50.0),
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('400010 Product Sales',                0.0,            200.0,          -200.0),
                ('600000 Expenses',                     0.0,            21000.0,        -21000.0),
                ('600010 Expenses',                     200.0,          0.0,            200.0),
                ('999989 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('Total General Ledger',                21550.0,        21550.0,        0.0),
            ],
            options,
        )

        options['unfold_all'] = True
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('121000 Account Receivable',           1000.0,         0.0,            1000.0),
                ('INV/2017/00001 2017_1_1',             1000.0,         0.0,            1000.0),
                ('Total 121000 Account Receivable',     1000.0,         0.0,            1000.0),
                ('211000 Account Payable',              100.0,          0.0,            100.0),
                ('Initial Balance',                     100.0,          0.0,            100.0),
                ('Total 211000 Account Payable',        100.0,          0.0,            100.0),
                ('211010 Account Payable',              50.0,           0.0,            50.0),
                ('Initial Balance',                     50.0,           0.0,            50.0),
                ('Total 211010 Account Payable',        50.0,           0.0,            50.0),
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('INV/2017/00001 2017_1_2',             2000.0,         0.0,            2000.0),
                ('INV/2017/00001 2017_1_3',             3000.0,         0.0,            5000.0),
                ('INV/2017/00001 2017_1_4',             4000.0,         0.0,            9000.0),
                ('INV/2017/00001 2017_1_5',             5000.0,         0.0,            14000.0),
                ('INV/2017/00001 2017_1_6',             6000.0,         0.0,            20000.0),
                ('Total 400000 Product Sales',          20000.0,        0.0,            20000.0),
                ('400010 Product Sales',                0.0,            200.0,          -200.0),
                ('BNK1/2017/00001 2017_2_2',            0.0,            200.0,          -200.0),
                ('Total 400010 Product Sales',          0.0,            200.0,          -200.0),
                ('600000 Expenses',                     0.0,            21000.0,        -21000.0),
                ('INV/2017/00001 2017_1_7',             0.0,            6000.0,         -6000.0),
                ('INV/2017/00001 2017_1_8',             0.0,            7000.0,         -13000.0),
                ('INV/2017/00001 2017_1_9',             0.0,            8000.0,         -21000.0),
                ('Total 600000 Expenses',               0.0,            21000.0,        -21000.0),
                ('600010 Expenses',                     200.0,          0.0,            200.0),
                ('BNK1/2017/00001 2017_2_1',            200.0,          0.0,            200.0),
                ('Total 600010 Expenses',               200.0,          0.0,            200.0),
                ('999989 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('Total General Ledger',                21550.0,        21550.0,        0.0),
            ],
            options,
        )

    def test_general_ledger_multiple_years_initial_balance(self):
        # Entries in 2015 for company_1 to test the initial balance.
        move_2015_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2015-01-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2015_1_1',     'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2015_1_2',     'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2015_1_3',     'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2015_1.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('121000 Account Receivable',           1000.0,         0.0,            1000.0),
                ('211000 Account Payable',              200.0,          0.0,            200.0),
                ('211010 Account Payable',              50.0,           0.0,            50.0),
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('400010 Product Sales',                0.0,            200.0,          -200.0),
                ('600000 Expenses',                     0.0,            21000.0,        -21000.0),
                ('600010 Expenses',                     200.0,          0.0,            200.0),
                ('999989 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('999999 Undistributed Profits/Losses', 400.0,          600.0,          -200.0),
                ('Total General Ledger',                21850.0,        21850.0,        0.0),
            ],
            options,
        )

        options['unfold_all'] = True

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('121000 Account Receivable',           1000.0,         0.0,            1000.0),
                ('INV/2017/00001 2017_1_1',             1000.0,         0.0,            1000.0),
                ('Total 121000 Account Receivable',     1000.0,         0.0,            1000.0),
                ('211000 Account Payable',              200.0,          0.0,            200.0),
                ('Initial Balance',                     200.0,          0.0,            200.0),
                ('Total 211000 Account Payable',        200.0,          0.0,            200.0),
                ('211010 Account Payable',              50.0,           0.0,            50.0),
                ('Initial Balance',                     50.0,           0.0,            50.0),
                ('Total 211010 Account Payable',        50.0,           0.0,            50.0),
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('INV/2017/00001 2017_1_2',             2000.0,         0.0,            2000.0),
                ('INV/2017/00001 2017_1_3',             3000.0,         0.0,            5000.0),
                ('INV/2017/00001 2017_1_4',             4000.0,         0.0,            9000.0),
                ('INV/2017/00001 2017_1_5',             5000.0,         0.0,            14000.0),
                ('INV/2017/00001 2017_1_6',             6000.0,         0.0,            20000.0),
                ('Total 400000 Product Sales',          20000.0,        0.0,            20000.0),
                ('400010 Product Sales',                0.0,            200.0,          -200.0),
                ('BNK1/2017/00001 2017_2_2',            0.0,            200.0,          -200.0),
                ('Total 400010 Product Sales',          0.0,            200.0,          -200.0),
                ('600000 Expenses',                     0.0,            21000.0,        -21000.0),
                ('INV/2017/00001 2017_1_7',             0.0,            6000.0,         -6000.0),
                ('INV/2017/00001 2017_1_8',             0.0,            7000.0,         -13000.0),
                ('INV/2017/00001 2017_1_9',             0.0,            8000.0,         -21000.0),
                ('Total 600000 Expenses',               0.0,            21000.0,        -21000.0),
                ('600010 Expenses',                     200.0,          0.0,            200.0),
                ('BNK1/2017/00001 2017_2_1',            200.0,          0.0,            200.0),
                ('Total 600010 Expenses',               200.0,          0.0,            200.0),
                ('999989 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('999999 Undistributed Profits/Losses', 400.0,          600.0,          -200.0),
                ('Total General Ledger',              21850.0,        21850.0,             0.0),
            ],
            options,
        )

    def test_general_ledger_load_more(self):
        ''' Test unfolding a line to use the load more. '''
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.env.company.ids))
        self.report.load_more_limit = 2

        # To test the inital balance with load more
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-02'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_3_1',     'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_3_2',     'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_3_3',     'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_3_4',     'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_3_5',     'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_3_6',     'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_3_7',     'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_3_8',     'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_3_9',     'account_id': self.company_data['default_account_expense'].id}),
            ],
        })
        move.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-02'), fields.Date.from_string('2017-12-31'))
        parent_line_id = self.report._get_generic_line_id(model_name='account.report.line', value=self.env.ref("account_reports.general_ledger_custom_engine_line").id)
        account_revenue_line_id = self.report._get_generic_line_id(model_name='account.account', value=self.company_data['default_account_revenue'].id, markup={'groupby': 'account_or_unaff_id'}, parent_line_id=parent_line_id)
        options['unfolded_lines'] = [account_revenue_line_id]
        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            report_lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('121000 Account Receivable',           2000.0,         0.0,            2000.0),
                ('211000 Account Payable',              100.0,          0.0,            100.0),
                ('400000 Product Sales',                40000.0,        0.0,            40000.0),
                ('Initial Balance',                     20000.0,        0.0,            20000.0),
                ('INV/2017/00002 2017_3_2',             2000.0,         0.0,            22000.0),
                ('Load more...',                        '',             '',             ''),
                ('Total 400000 Product Sales',          40000.0,        0.0,            40000.0),
                ('600000 Expenses',                     0.0,            42000.0,        -42000.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('Total General Ledger',                42300.0,        42300.0,        0.0),
            ],
            options,
        )

        load_more_1 = self.report.get_expanded_lines(
            options,
            report_lines[4]['id'],
            report_lines[7]['groupby'],
            '_report_expand_unfoldable_line_with_groupby',
            report_lines[7]['progress'],
            report_lines[7]['offset'],
            None,
        )

        self.assertLinesValues(
            load_more_1,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('INV/2017/00002 2017_3_3',             3000.0,         0.0,            25000.0),
                ('INV/2017/00002 2017_3_4',             4000.0,         0.0,            29000.0),
                ('Load more...',                        '',             '',             ''),
            ],
            options,
        )

        load_more_2 = self.report.get_expanded_lines(
            options,
            report_lines[4]['id'],
            load_more_1[2]['groupby'],
            '_report_expand_unfoldable_line_with_groupby',
            load_more_1[2]['progress'],
            load_more_1[2]['offset'],
            None,
        )

        self.assertLinesValues(
            load_more_2,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('INV/2017/00002 2017_3_5',             5000.0,         0.0,            34000.0),
                ('INV/2017/00002 2017_3_6',             6000.0,         0.0,            40000.0),
            ],
            options,
        )

    def test_general_ledger_foreign_currency_account(self):
        ''' Ensure the total in foreign currency of an account is displayed only if all journal items are sharing the
        same currency.
        '''
        self.env.user.group_ids |= self.env.ref('base.group_multi_currency')

        foreign_curr_account = self.env['account.account'].create({
            'name': 'foreign_curr_account',
            'code': 'test',
            'account_type': 'liability_current',
            'currency_id': self.other_currency.id,
        })

        move_2016 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 100.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -300.0,
                    'currency_id': self.other_currency.id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2016.action_post()

        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'amount_currency': 1000.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 1000.0,
                    'amount_currency': -2000.0,
                    'currency_id': self.other_currency.id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2017.action_post()
        move_2017.line_ids.flush_recordset()

        # Init options.
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        parent_line_id = self.report._get_generic_line_id(model_name='account.report.line', value=self.env.ref("account_reports.general_ledger_custom_engine_line").id)
        account_revenue_line_id = self.report._get_generic_line_id(model_name='account.account', value=foreign_curr_account.id, markup={'groupby': 'account_or_unaff_id'}, parent_line_id=parent_line_id)
        options['unfolded_lines'] = [account_revenue_line_id]
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Amount_currency Debit           Credit          Balance
            [   0,                                      3,              4,              5,              6],
            [
                ('121000 Account Receivable',           '',             2100.0,         0.0,            2100.0),
                ('211000 Account Payable',              '',             100.0,          0.0,            100.0),
                ('211010 Account Payable',              '',             50.0,           0.0,            50.0),
                ('400000 Product Sales',                '',             20000.0,        0.0,            20000.0),
                ('400010 Product Sales',                '',             0.0,            200.0,          -200.0),
                ('600000 Expenses',                     '',             0.0,            21000.0,        -21000.0),
                ('600010 Expenses',                     '',             200.0,          0.0,            200.0),
                ('999989 Undistributed Profits/Losses', '',             0.0,            50.0,           -50.0),
                ('999999 Undistributed Profits/Losses', '',             200.0,          300.0,          -100.0),
                ('test foreign_curr_account',           -2300.0,        0.0,            1100.0,         -1100.0),
                ('Initial Balance',                     -300.0,         0.0,            100.0,          -100.0),
                ('INV/2017/00002 curr_2',               -2000.0,        0.0,            1000.0,         -1100.0),
                ('Total test foreign_curr_account',     -2300.0,        0.0,            1100.0,         -1100.0),
                ('Total General Ledger',                '',             22650.0,        22650.0,        0.0),
            ],
            options,
            currency_map={3: {'currency': self.other_currency}},
        )

    def test_general_ledger_filter_search_bar_print(self):
        """ Test the lines generated when a user filters on the search bar and prints the report """
        options = self._generate_options(self.report, '2017-01-01', '2017-12-31', default_options={'export_mode': 'print'})
        options['filter_search_bar'] = '400'
        options['unfold_all'] = True
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      3,              4,              5],
            [
                ('400000 Product Sales',                20000.0,          0.0,          20000.0),
                ('INV/2017/00001 2017_1_2',              2000.0,          0.0,           2000.0),
                ('INV/2017/00001 2017_1_3',              3000.0,          0.0,           5000.0),
                ('INV/2017/00001 2017_1_4',              4000.0,          0.0,           9000.0),
                ('INV/2017/00001 2017_1_5',              5000.0,          0.0,           14000.0),
                ('INV/2017/00001 2017_1_6',              6000.0,          0.0,           20000.0),
                ('Total 400000 Product Sales',          20000.0,          0.0,          20000.0),
                ('400010 Product Sales',                    0.0,        200.0,           -200.0),
                ('BNK1/2017/00001 2017_2_2',                0.0,        200.0,           -200.0),
                ('Total 400010 Product Sales',              0.0,        200.0,           -200.0),
                ('Total General Ledger',                20000.0,        200.0,          19800.0),
            ],
            options,
        )

        options['filter_search_bar'] = '999'
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                          Debit           Credit          Balance
            [   0,                                            3,              4,              5],
            [
                ('999989 Undistributed Profits/Losses',         0.0,           50.0,           -50.0),
                ('999999 Undistributed Profits/Losses',       200.0,          300.0,          -100.0),
                ('Total General Ledger',                      200.0,          350.0,          -150.0),
            ],
            options,
        )

    def test_general_ledger_income_expense_initial_balance(self):
        ''' Test that when the report period does not start at the beginning of the FY,
            any AMLs prior to the report period but after the beginning of the FY are
            displayed in the initial balance for Income and Expense accounts. '''

        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.env.company.ids))

        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-02-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({'debit': 1000.0, 'credit':    0.0, 'name': '2017_3_1', 'account_id': self.company_data['default_account_receivable'].id}),
                Command.create({'debit':    0.0, 'credit': 1000.0, 'name': '2017_3_2', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2017.action_post()

        # Init options.
        options = self._generate_options(self.report, '2017-02-01', '2017-03-01')
        parent_line_id = self.report._get_generic_line_id(model_name='account.report.line', value=self.env.ref("account_reports.general_ledger_custom_engine_line").id)
        account_revenue_line_id = self.report._get_generic_line_id(model_name='account.account', value=self.company_data['default_account_revenue'].id, markup={'groupby': 'account_or_unaff_id'}, parent_line_id=parent_line_id)
        options['unfolded_lines'] = [account_revenue_line_id]
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                            3,             4,                5],
            [
                ('121000 Account Receivable',            2000.0,           0.0,           2000.0),
                ('211000 Account Payable',                100.0,           0.0,            100.0),
                ('400000 Product Sales',                20000.0,        1000.0,          19000.0),
                ('Initial Balance',                     20000.0,           0.0,          20000.0),
                ('INV/2017/00002 2017_3_2',                 0.0,        1000.0,          19000.0),
                ('Total 400000 Product Sales',          20000.0,        1000.0,          19000.0),
                ('600000 Expenses',                         0.0,       21000.0,         -21000.0),
                ('999999 Undistributed Profits/Losses',   200.0,         300.0,           -100.0),
                ('Total General Ledger',                22300.0,       22300.0,              0.0),
            ],
            options,
        )

    @freeze_time('2017-07-11')
    def test_tour_account_reports_search(self):
        move_07_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-07-10'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': '2017_1_1',
                        'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'name': '2017_1_2',
                        'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_07_2017.action_post()

        self.start_tour("/odoo", 'account_reports_search', login=self.env.user.login)

    def test_general_ledger_hierarchy_non_numerical_column_value(self):
        """
            This test will check the value of the different (non-numerical) columns of the general ledger in case the
            hierarchy options is enabled
        """
        options = self._generate_options(self.report, '2017-01-01', '2017-12-31')
        options['hierarchy'] = True

        # String and Date figure type should be empty when using hierarchy.

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                     Date           Partner
            [0,                             1,                2],
            [
                ('(No Group)',             '',               ''),
                ('Total General Ledger',   '',               ''),
            ],
            options,
        )

    def test_general_ledger_same_date_ordering(self):
        self.env.company.account_sale_tax_id = None
        self.env.company.totals_below_sections = False

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2010-01-01'), fields.Date.from_string('2010-01-01'), default_options={'unfold_all': True})

        move_1 = self.init_invoice('out_invoice', invoice_date='2010-01-01', amounts=[100])
        move_2 = self.init_invoice('out_invoice', invoice_date='2010-01-01', amounts=[200])

        # Make sure no sequence is set on them by default, so that move_2 can receive a lower sequence when posting
        (move_1 + move_2).write({'name': ''})

        # Post the moves in reverse order than the one they were created in, so that their line ids' respective order does not match their sequences'
        move_2.action_post()
        move_1.action_post()

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                      Debit       Credit      Balance
            [   0,                                           3,           4,          5],
            [
                ('121000 Account Receivable',            300.0,         0.0,      300.0),
                (move_2.name,                            200.0,         0.0,      200.0),
                (move_1.name,                            100.0,         0.0,      300.0),
                ('400000 Product Sales',                   0.0,       300.0,     -300.0),
                (f"{move_2.name} test line",               0.0,       200.0,     -200.0),
                (f"{move_1.name} test line",               0.0,       100.0,     -300.0),
                ('Total General Ledger',                 300.0,       300.0,        0.0),
            ],
            options
        )

    def test_general_ledger_initial_balance_with_limit(self):
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)
        self.init_invoice('out_invoice', invoice_date='2009-01-01', amounts=[100], post=True)

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, '2010-01-01', '2010-01-01', default_options={'unfold_all': True})
        self.env.company.totals_below_sections = False
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                          Debit       Credit      Balance
            [   0,                                               3,           4,          5],
            [
                ('121000 Account Receivable',               2500.0,         0.0,     2500.0),
                ("Initial Balance",                         2500.0,         0.0,     2500.0),
                ('999999 Undistributed Profits/Losses',        0.0,      2500.0,    -2500.0),
                ('Total General Ledger',                    2500.0,      2500.0,        0.0),
            ],
            options
        )

    def test_general_ledger_multicurrency(self):
        self.env.user.group_ids |= self.env.ref('base.group_multi_currency')
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2014-01-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'amount_currency': 300,    'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': self.company_data['default_account_payable'].id, 'currency_id': self.other_currency.id}),
                (0, 0, {'amount_currency': 600,    'debit': 200.0,     'credit': 0.0,      'name': '2016_1_2',     'account_id': self.company_data['default_account_expense'].id, 'currency_id': self.other_currency.id}),
                (0, 0, {'amount_currency': -900,   'debit': 0.0,       'credit': 300.0,    'name': '2016_1_3',     'account_id': self.company_data['default_account_revenue'].id, 'currency_id': self.other_currency.id}),
            ],
        })
        move.action_post()

        options = self._generate_options(self.report, '2014-01-01', '2014-01-01', default_options={'unfold_all': True})
        self.env.company.totals_below_sections = False
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                          amount_currency           Debit       Credit      Balance
            [   0,                                          3,              4,           5,          6],
            [
                ('211000 Account Payable',                 '',          100.0,         0.0,      100.0),
                ("MISC/2014/01/0001 2016_1_1",          300.0,          100.0,         0.0,      100.0),
                ('400000 Product Sales',                   '',            0.0,       300.0,     -300.0),
                ("MISC/2014/01/0001 2016_1_3",         -900.0,            0.0,       300.0,     -300.0),
                ('600000 Expenses',                        '',          200.0,         0.0,      200.0),
                ("MISC/2014/01/0001 2016_1_2",          600.0,          200.0,         0.0,      200.0),
                ('Total General Ledger',                   '',          300.0,       300.0,        0.0),
            ],
            options,
            currency_map={3: {'currency': self.other_currency}},
        )

    def test_general_ledger_unfold_all(self):
        """
        Check that the batched version of the report is consistent with the report non batched
        """
        self.env.company.totals_below_sections = False
        options = self._generate_options(self.report, '2017-01-01', '2017-12-31', default_options={'unfold_all': False})

        folded_report_lines = self.report._get_lines(options)
        lines_to_unfold = []
        for line in folded_report_lines:
            if line.get('unfoldable'):
                lines_to_unfold.append(line['id'])

        non_batched_options = self._generate_options(self.report, '2017-01-01', '2017-12-31', default_options={'unfold_all': False, 'unfolded_lines': lines_to_unfold})
        non_batched_report_lines = self.report._get_lines(non_batched_options)

        batched_options = self._generate_options(self.report, '2017-01-01', '2017-12-31', default_options={'unfold_all': True})
        batched_report_lines = self.report._get_lines(batched_options)

        self.assertEqual(len(non_batched_report_lines), len(batched_report_lines), "Different number of lines of batched report and non batched report")
        for line_batched, line_non_batched in zip(batched_report_lines, non_batched_report_lines):
            self.assertDictEqual(line_batched, line_non_batched)
