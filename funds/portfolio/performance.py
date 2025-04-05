import datetime
from decimal import Decimal

from django.db.models import QuerySet
from django_rq import job

from funds.portfolio.models import Portfolio, PortfolioWeek
from holdings.models import (
    HoldingAccountAction,
    HoldingAccountGeneration,
    HoldingAccountSale,
)
from holdings.positions.action_list import ActionList
from holdings.positions.generation_list import GenerationList
from holdings.positions.sale_list import SaleList


class PerformanceQuery:
    portfolio: Portfolio
    start_date: datetime.date
    end_date: datetime.date

    _actions: QuerySet[HoldingAccountAction] | None = None
    _sales: QuerySet[HoldingAccountSale] | None = None
    _generations: QuerySet[HoldingAccountGeneration] | None = None

    def __init__(
        self, portfolio: Portfolio, start_date: datetime.date, end_date: datetime.date
    ) -> None:
        self.portfolio = portfolio
        self.start_date = start_date
        self.end_date = end_date

    @property
    def actions(self) -> QuerySet[HoldingAccountAction]:
        if self._actions is not None:
            return self._actions

        self._actions = HoldingAccountAction.objects.filter(
            position__holding_account__portfolio=self.portfolio,
            purchased_on__gte=self.start_date,
            purchased_on__lt=self.end_date,
        )
        assert self._actions is not None
        return self._actions

    @property
    def sales(self) -> QuerySet[HoldingAccountSale]:
        if self._sales is not None:
            return self._sales

        self._sales = HoldingAccountSale.objects.filter(
            position__holding_account__portfolio=self.portfolio,
            sale_date__gte=self.start_date,
            sale_date__lt=self.end_date,
        )
        assert self._sales is not None
        return self._sales

    @property
    def generations(self) -> QuerySet[HoldingAccountGeneration]:
        if self._generations is not None:
            return self._generations

        self._generations = HoldingAccountGeneration.objects.filter(
            position__holding_account__portfolio=self.portfolio,
            date__gte=self.start_date,
            date__lt=self.end_date,
        )
        assert self._generations is not None
        return self._generations


class Performance:
    query: PerformanceQuery

    _action_list: ActionList | None = None
    _sale_list: SaleList | None = None
    _generation_list: GenerationList | None = None

    def __init__(self, query: PerformanceQuery) -> None:
        self.query = query

    @property
    def actions(self) -> ActionList:
        if self._action_list is not None:
            return self._action_list

        self._action_list = ActionList(
            a.position_action for a in self.query.actions.all()
        )
        return self._action_list

    @property
    def sales(self) -> SaleList:
        if self._sale_list is not None:
            return self._sale_list

        self._sale_list = SaleList(s.position_sale for s in self.query.sales.all())
        return self._sale_list

    @property
    def generations(self) -> GenerationList:
        if self._generation_list is not None:
            return self._generation_list

        self._generation_list = GenerationList(
            s.position_generation for s in self.query.generations.all()
        )
        return self._generation_list

    @property
    def sale_profit(self) -> Decimal:
        return self.sales.total_profit()

    @property
    def sale_interest(self) -> Decimal:
        return self.sales.total_interest()

    @property
    def generation_profit(self) -> Decimal:
        return self.generations.total_profit()

    @property
    def total_profit(self) -> Decimal:
        return self.sale_profit + self.generation_profit


@job("default")
def sync_performance_weeks(self: Portfolio) -> None:
    first_action = (
        HoldingAccountAction.objects.filter(
            position__holding_account__portfolio=self,
        )
        .order_by("purchased_on")
        .first()
    )
    if first_action is None:
        return

    date = first_action.purchased_on
    if date.weekday() != 0:
        date = date - datetime.timedelta(days=date.weekday())

    today = datetime.date.today()
    while date < today:
        week, created = self.weeks.get_or_create(date=date)
        if created or (today - date).days < 14:
            sync_performance_week.delay(week)

        date += datetime.timedelta(days=7)


@job("low")
def sync_performance_week(self: PortfolioWeek) -> None:
    performance = self.performance
    self.sale_profit = performance.sale_profit
    self.sale_interest = performance.sale_interest
    self.generation_profit = performance.generation_profit
    self.net_cost_basis = performance.actions.net_cost_basis()
    self.save()
